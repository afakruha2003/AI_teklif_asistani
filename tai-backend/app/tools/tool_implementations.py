from __future__ import annotations

import time
import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Product, KnowledgeEntry, Quote, QuoteItem, ToolCallLog, Customer, PriceRule,
    QuoteItemStatus, ToolCallStatus,
)
from app.schemas import (
    SearchProductsInput, GetKnowledgeInput, GetQuoteInput,
    AddToQuoteInput, UpdateQuoteItemInput, ReplaceWithAlternativeInput,
)


# ─────────────────────────────────────────────────────────────────────────────
# Serializers
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_product(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "price_try": float(p.price_try),
        "stock": p.stock,
        "sku": p.sku,
        "aliases": p.aliases or [],
        "tags": p.tags or [],
        "is_active": p.is_active,
        "alternative_product_id": p.alternative_product_id,
    }


def _serialize_knowledge(e: KnowledgeEntry) -> dict:
    # Seed verisi "body" field'ını kullanıyor; ORM modeli bunu "content"
    # veya "body" olarak map etmiş olabilir — her ikisini de dene.
    body = getattr(e, "content", None) or getattr(e, "body", None) or ""
    return {
        "knowledge_id": e.id,
        "title": e.title,
        "content": body,
        "category": e.category,
        "tags": e.tags or [],
    }


def _serialize_quote_item(item: QuoteItem, product_name: Optional[str]) -> dict:
    qty = item.quantity
    unit = float(item.unit_price_try)
    disc = float(item.discount_pct)
    return {
        "item_id": item.id,
        "product_id": item.product_id,
        "product_name": product_name,
        "quantity": qty,
        "unit_price_try": unit,
        "discount_pct": disc,
        "line_total_try": round(qty * unit * (1 - disc / 100), 2),
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "is_backorder": item.is_backorder,
    }


def _serialize_quote(quote: Quote, product_names: Dict[str, str]) -> dict:
    serialized_items = [
        _serialize_quote_item(item, product_names.get(item.product_id))
        for item in quote.items
    ]
    active_items = [i for i in serialized_items if i["status"] == "active"]
    total_amount = sum(i["line_total_try"] for i in active_items)
    return {
        "quote_id": quote.id,
        "customer_id": quote.customer_id,
        "status": quote.status,
        "items": serialized_items,
        "active_items_count": len(active_items),
        "total_try": round(total_amount, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Türkçe soru/fiil ekleri ve genel gürültü kelimeleri — bunlar token scoring'e
# katılmaz, yanlış eşleşmeleri önler.
_STOPWORDS = {
    # Türkçe soru/fiil ekleri
    "var", "mı", "mi", "mu", "mü", "mı?", "mi?", "mu?", "mü?",
    "ekler", "misin", "misin?", "ekleyebilir", "ekleyebilir?",
    "nedir", "nedir?", "nasıl", "nasıl?", "kaç", "ne", "bir",
    "için", "ile", "ve", "veya", "ya", "da", "de", "bu", "şu",
    "altı", "üstü", "altında", "üstünde", "aşağı", "yukarı",
    "öner", "önerir", "önerin", "tavsiye", "istiyorum", "istiyorum.",
    "lütfen", "acaba", "bana", "benim",
    # Para birimi ve fiyat bağlamı kelimeleri — bunlar hiçbir ürün
    # adında geçmez, token matching'i bozar.
    "tl", "try", "lira", "₺", "fiyat", "fiyatlı", "fiyatı",
    # Çok genel ürün kelimeleri — kategori filtresi olmadan anlamsız
    "ürün", "ürünler", "ürününü", "ürünü",
    # Fiyat kısıtı ifadeleri
    "altı", "üstü", "altında", "üzerinde", "üstünde",
    "ucuz", "ekonomik", "uygun", "uygun fiyatlı",
}

# Sayı token'larını da çıkar — fiyat parsing zaten regex ile yapılıyor.
_NUMBER_RE = __import__("re").compile(r"^\d+([.,]\d+)?$")


def _tokenize(text: str) -> list[str]:
    """Metni anlamlı token'lara böler; stopword ve sayıları çıkarır."""
    tokens = text.lower().split()
    result = []
    for t in tokens:
        # noktalama temizle
        clean = t.strip("?.!,;:()")
        if not clean:
            continue
        if clean in _STOPWORDS:
            continue
        if _NUMBER_RE.match(clean):
            continue
        result.append(clean)
    return result


def _clean_query(query: str) -> str:
    for token in ("var mı?", "var mi?", "ekler misin?", "ekler misin",
                  "ekleyebilir misin?", "ekleyebilir misin", "?", "."):
        query = query.replace(token, "")
    return " ".join(query.split()).strip()


def _score_product(p: Product, tokens: list[str]) -> int:
    """
    Token bazlı scoring: her anlamlı token ayrı ayrı eşleştirilir.
    Tam substring eşleşmesi yerine token düzeyinde kontrol yapılır.
    Bu sayede "el terminali öner" → "el terminali" ürününü bulur.
    """
    if not tokens:
        return 1  # query yoksa tüm ürünler eşit

    name_lower = p.name.lower()
    desc_lower = (p.description or "").lower()
    aliases_lower = [a.lower() for a in (p.aliases or [])]
    tags_lower = [t.lower() for t in (p.tags or [])]

    score = 0
    for token in tokens:
        if token in name_lower:
            score += 10
        if token in desc_lower:
            score += 3
        if any(token in a for a in aliases_lower):
            score += 8
        if any(token in t for t in tags_lower):
            score += 5
    return score


def _score_knowledge(e: KnowledgeEntry, tokens: list[str]) -> int:
    """
    Token bazlı scoring: "iade politikası nedir" → ["iade", "politikası"]
    token'larından "iade" knowledge entry title/content/body'de eşleşir.
    """
    if not tokens:
        return 1

    title_lower = e.title.lower()
    # Seed "body", ORM modeli "content" veya "body" kullanıyor olabilir
    raw_body = getattr(e, "content", None) or getattr(e, "body", None) or ""
    content_lower = raw_body.lower()
    tags_lower = [t.lower() for t in (e.tags or [])]

    score = 0
    for token in tokens:
        if token in title_lower:
            score += 10
        if token in content_lower:
            score += 5
        if any(token in t for t in tags_lower):
            score += 7
    return score


async def _log_tool_call(
    db: AsyncSession,
    session_id: str,
    tool_name: str,
    input_data: dict,
    output_data: dict,
    status: ToolCallStatus,
    quote_delta: Optional[dict],
    sequence_num: int,
    duration_ms: int,
    idempotency_key: Optional[str] = None,
) -> None:
    log_entry = ToolCallLog(
        id=str(uuid.uuid4()),
        session_id=session_id,
        tool_name=tool_name,
        input_data=input_data,
        output_data=output_data,
        status=status,
        quote_delta=quote_delta,
        sequence_num=sequence_num,
        duration_ms=duration_ms,
        idempotency_key=idempotency_key,
    )
    db.add(log_entry)


async def _get_customer_segment(db: AsyncSession, customer_id: Optional[str]) -> str:
    if not customer_id:
        return "standard"
    customer = await db.get(Customer, customer_id)
    if not customer:
        return "standard"
    return customer.segment.value if hasattr(customer.segment, "value") else str(customer.segment)


async def _get_discount(
    db: AsyncSession,
    product_id: str,
    category: str,
    segment: str,
    quantity: int,
) -> float:
    rule_stmt = (
        select(PriceRule)
        .where(
            PriceRule.is_active == True,
            or_(PriceRule.segment == segment, PriceRule.segment == None),
            or_(PriceRule.product_id == product_id, PriceRule.product_id == None),
            or_(func.lower(PriceRule.category) == category.lower(), PriceRule.category == None),
        )
        .order_by(PriceRule.priority.desc())
    )
    result = await db.execute(rule_stmt)
    rules = result.scalars().all()
    for rule in rules:
        if quantity >= rule.min_quantity:
            return float(rule.discount_pct)
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Tool: search_products
# ─────────────────────────────────────────────────────────────────────────────

async def search_products(
    db: AsyncSession,
    params: SearchProductsInput,
    session_id: str,
    sequence_num: int = 0,
    skip_logging: bool = False,
) -> Dict[str, Any]:
    start_time = time.monotonic()
    stmt = select(Product).where(Product.is_active == True)

    if params.max_price_try is not None:
        stmt = stmt.where(Product.price_try <= params.max_price_try)
    if params.category:
        stmt = stmt.where(func.lower(Product.category) == params.category.lower())
    if params.in_stock_only:
        stmt = stmt.where(Product.stock > 0)

    result = await db.execute(stmt.limit(200))
    products: List[Product] = list(result.scalars().all())

    if params.query:
        # FIX: token bazlı scoring — tam string eşleşmesi yerine her anlamlı
        # token ayrı ayrı aranır. "el terminali öner" gibi doğal dil sorgular
        # artık doğru ürünleri buluyor.
        tokens = _tokenize(_clean_query(params.query))
        if tokens:
            scored: list[tuple[Product, int]] = []
            for p in products:
                score = _score_product(p, tokens)
                if score > 0:
                    scored.append((p, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            if scored:
                # En az bir token eşleşti — sıralı listeyi döndür
                products = [p for p, _ in scored[: params.limit]]
            else:
                # Hiçbir token ürün adı/alias/tag'inde eşleşmedi (örn. "ürün",
                # "tl" gibi genel kelimeler). Bu durumda zaten fiyat/stok
                # filtresiyle daraltılmış tüm ürünleri döndür — kullanıcı
                # bütçe belirtmiş ama kategori belirtmemiş demektir.
                products = products[: params.limit]
        else:
            # Tüm token'lar stopword — filtresiz döndür
            products = products[: params.limit]
    else:
        products = products[: params.limit]

    if params.tags:
        target = [t.lower() for t in params.tags]
        products = [p for p in products if any(t.lower() in target for t in (p.tags or []))]

    serialized = [_serialize_product(p) for p in products]
    output = {"products": serialized, "count": len(serialized)}

    duration_ms = int((time.monotonic() - start_time) * 1000)
    if not skip_logging:
        await _log_tool_call(
            db, session_id, "search_products", params.model_dump(), output,
            ToolCallStatus.success, None, sequence_num, duration_ms,
        )
        await db.commit()
    return output


# ─────────────────────────────────────────────────────────────────────────────
# Tool: get_knowledge_entries
# ─────────────────────────────────────────────────────────────────────────────

async def get_knowledge_entries(
    db: AsyncSession,
    params: GetKnowledgeInput,
    session_id: str,
    sequence_num: int = 0,
    skip_logging: bool = False,
) -> Dict[str, Any]:
    start_time = time.monotonic()
    stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)

    if params.category:
        stmt = stmt.where(func.lower(KnowledgeEntry.category) == params.category.lower())

    result = await db.execute(stmt.limit(100))
    entries: List[KnowledgeEntry] = list(result.scalars().all())

    if params.query:
        # FIX: token bazlı scoring — "İade politikası nedir?" → ["iade",
        # "politikası"] token'ları ayrı ayrı eşleştirilir. Önceki tam-string
        # yaklaşımında soru ifadesi hiçbir entry'de geçmediğinden hepsi
        # score=0 alıp filtreleniyordu.
        tokens = _tokenize(params.query)
        if tokens:
            scored: list[tuple[KnowledgeEntry, int]] = []
            for e in entries:
                score = _score_knowledge(e, tokens)
                if score > 0:
                    scored.append((e, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            entries = [e for e, _ in scored[: params.limit]]
        else:
            # Tüm token'lar stopword — filtresiz döndür
            entries = entries[: params.limit]
    else:
        entries = entries[: params.limit]

    if params.tags:
        target = [t.lower() for t in params.tags]
        entries = [e for e in entries if any(t.lower() in target for t in (e.tags or []))]

    serialized = [_serialize_knowledge(e) for e in entries]
    output = {"knowledge_entries": serialized, "count": len(serialized)}

    duration_ms = int((time.monotonic() - start_time) * 1000)
    if not skip_logging:
        await _log_tool_call(
            db, session_id, "get_knowledge_entries", params.model_dump(), output,
            ToolCallStatus.success, None, sequence_num, duration_ms,
        )
        await db.commit()
    return output


# ─────────────────────────────────────────────────────────────────────────────
# Tool: get_quote
# ─────────────────────────────────────────────────────────────────────────────

async def get_quote(
    db: AsyncSession,
    params: GetQuoteInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    start_time = time.monotonic()

    stmt = (
        select(Quote)
        .where(Quote.id == params.quote_id)
        .options(selectinload(Quote.items).selectinload(QuoteItem.product))
    )
    result = await db.execute(stmt)
    quote = result.scalar_one_or_none()

    if not quote:
        output = {"error": f"Quote {params.quote_id} not found"}
        status = ToolCallStatus.error
    else:
        product_names: Dict[str, str] = {}
        for item in quote.items:
            if item.product:
                product_names[item.product_id] = item.product.name

        output = _serialize_quote(quote, product_names)
        status = ToolCallStatus.success

    duration_ms = int((time.monotonic() - start_time) * 1000)
    await _log_tool_call(
        db, session_id, "get_quote", params.model_dump(), output,
        status, None, sequence_num, duration_ms,
    )
    await db.commit()
    return output


# ─────────────────────────────────────────────────────────────────────────────
# Tool: add_to_quote
# ─────────────────────────────────────────────────────────────────────────────

async def add_to_quote(
    db: AsyncSession,
    params: AddToQuoteInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    start_time = time.monotonic()

    if params.idempotency_key:
        existing = await db.execute(
            select(ToolCallLog).where(ToolCallLog.idempotency_key == params.idempotency_key)
        )
        if existing.scalar_one_or_none():
            output = {"idempotent": True, "message": "Duplicate request ignored"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(
                db, session_id, "add_to_quote", params.model_dump(), output,
                ToolCallStatus.success, None, sequence_num, duration_ms,
            )
            await db.commit()
            return output

    product = await db.get(Product, params.product_id)
    if not product or not product.is_active:
        output = {"error": f"Product {params.product_id} not found or inactive"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "add_to_quote", params.model_dump(), output,
                             ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    product_id = product.id
    product_name = product.name
    product_price = float(product.price_try)
    product_stock = product.stock
    product_category = product.category

    if params.max_price_try is not None and product_price > params.max_price_try:
        output = {"error": "Product price exceeds max_price_try", "rule_violated": "price_limit"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "add_to_quote", params.model_dump(), output,
                             ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    quote = await db.get(Quote, params.quote_id)
    customer_id = quote.customer_id if quote else None
    segment = await _get_customer_segment(db, customer_id)

    existing_item_result = await db.execute(
        select(QuoteItem).where(
            QuoteItem.quote_id == params.quote_id,
            QuoteItem.product_id == params.product_id,
            QuoteItem.status == QuoteItemStatus.active,
        )
    )
    curr_item = existing_item_result.scalar_one_or_none()

    curr_item_id = curr_item.id if curr_item else None
    curr_item_qty = curr_item.quantity if curr_item else 0
    simulated_qty = params.quantity + curr_item_qty

    applied_discount = await _get_discount(db, product_id, product_category, segment, simulated_qty)

    is_backorder = False
    if product_stock <= 0:
        if not params.allow_backorder:
            output = {"error": "Product is out of stock", "rule_violated": "out_of_stock",
                      "product_id": product_id}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "add_to_quote", params.model_dump(), output,
                                 ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output
        is_backorder = True

    if curr_item:
        curr_item.quantity = simulated_qty
        curr_item.discount_pct = applied_discount
        action = "quantity_increased"
        item_id = curr_item_id
        old_qty = curr_item_qty
        new_qty = simulated_qty
    else:
        new_item = QuoteItem(
            id=str(uuid.uuid4()),
            quote_id=params.quote_id,
            product_id=product_id,
            quantity=params.quantity,
            unit_price_try=product_price,
            discount_pct=applied_discount,
            status=QuoteItemStatus.active,
            is_backorder=is_backorder,
        )
        db.add(new_item)
        action = "item_added"
        item_id = new_item.id
        old_qty = 0
        new_qty = params.quantity

    quote_delta = {
        "action": action,
        "item_id": item_id,
        "product_id": product_id,
        "product_name": product_name,
        "old_quantity": old_qty,
        "new_quantity": new_qty,
        "unit_price_try": product_price,
        "applied_discount_pct": applied_discount,
    }
    output = {"success": True, "quote_id": params.quote_id, **quote_delta}

    duration_ms = int((time.monotonic() - start_time) * 1000)
    await _log_tool_call(
        db, session_id, "add_to_quote", params.model_dump(), output,
        ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
        idempotency_key=params.idempotency_key,
    )
    await db.commit()
    return output


# ─────────────────────────────────────────────────────────────────────────────
# Tool: update_quote_item
# ─────────────────────────────────────────────────────────────────────────────

async def update_quote_item(
    db: AsyncSession,
    params: UpdateQuoteItemInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    start_time = time.monotonic()

    item = await db.get(QuoteItem, params.item_id)
    if not item or item.quote_id != params.quote_id:
        output = {"error": "Quote item not found"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                             ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    if item.status != QuoteItemStatus.active:
        output = {"error": "Cannot update non-active item"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                             ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    old_qty = item.quantity
    item_product_id = item.product_id
    item_is_backorder = item.is_backorder
    item_discount = float(item.discount_pct)

    product = await db.get(Product, item_product_id)
    product_stock = product.stock if product else 1
    product_category = product.category if product else ""

    if params.quantity == 0:
        item.status = QuoteItemStatus.removed
        action = "item_removed"
        new_qty = 0
        applied_discount = item_discount
    else:
        if product_stock <= 0 and not item_is_backorder:
            output = {"error": "Product is out of stock, cannot modify quantity",
                      "rule_violated": "out_of_stock"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                                 ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        quote = await db.get(Quote, params.quote_id)
        customer_id = quote.customer_id if quote else None
        segment = await _get_customer_segment(db, customer_id)
        applied_discount = await _get_discount(
            db, item_product_id, product_category, segment, params.quantity
        )
        item.quantity = params.quantity
        item.discount_pct = applied_discount
        action = "quantity_updated"
        new_qty = params.quantity

    quote_delta = {
        "action": action,
        "item_id": params.item_id,
        "old_quantity": old_qty,
        "new_quantity": new_qty,
        "applied_discount_pct": applied_discount,
    }
    output = {"success": True, "quote_id": params.quote_id, **quote_delta}

    duration_ms = int((time.monotonic() - start_time) * 1000)
    await _log_tool_call(
        db, session_id, "update_quote_item", params.model_dump(), output,
        ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
    )
    await db.commit()
    return output


# ─────────────────────────────────────────────────────────────────────────────
# Tool: replace_with_alternative
# ─────────────────────────────────────────────────────────────────────────────

async def replace_with_alternative(
    db: AsyncSession,
    params: ReplaceWithAlternativeInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    start_time = time.monotonic()

    old_item = await db.get(QuoteItem, params.item_id)
    if not old_item or old_item.quote_id != params.quote_id:
        output = {"error": "Item not found"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                             output, ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    if old_item.status != QuoteItemStatus.active:
        output = {"error": "Cannot replace non-active item"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                             output, ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    old_item_id = old_item.id
    old_product_id = old_item.product_id
    old_quantity = old_item.quantity

    alt_product_id = params.alternative_product_id
    if not alt_product_id:
        old_product = await db.get(Product, old_product_id)
        alt_product_id = old_product.alternative_product_id if old_product else None
        if not alt_product_id:
            output = {"error": "No alternative product specified"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

    alt_product = await db.get(Product, alt_product_id)
    if not alt_product or not alt_product.is_active:
        output = {"error": "Alternative product inactive"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                             output, ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    alt_product_name = alt_product.name
    alt_product_price = float(alt_product.price_try)
    alt_product_stock = alt_product.stock
    alt_product_category = alt_product.category

    if params.max_price_try is not None and alt_product_price > params.max_price_try:
        output = {"error": "Alternative price exceeds limit"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                             output, ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    if alt_product_stock <= 0:
        output = {"error": "Alternative out of stock"}
        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                             output, ToolCallStatus.error, None, sequence_num, duration_ms)
        await db.commit()
        return output

    quote = await db.get(Quote, params.quote_id)
    customer_id = quote.customer_id if quote else None
    segment = await _get_customer_segment(db, customer_id)
    applied_discount = await _get_discount(
        db, alt_product_id, alt_product_category, segment, old_quantity
    )

    new_item_id = str(uuid.uuid4())
    new_item = QuoteItem(
        id=new_item_id,
        quote_id=params.quote_id,
        product_id=alt_product_id,
        quantity=old_quantity,
        unit_price_try=alt_product_price,
        discount_pct=applied_discount,
        status=QuoteItemStatus.active,
        is_backorder=False,
    )
    db.add(new_item)

    old_item.status = QuoteItemStatus.replaced
    old_item.replaced_by_item_id = new_item_id

    quote_delta = {
        "action": "item_replaced",
        "old_item_id": old_item_id,
        "new_item_id": new_item_id,
        "old_product_id": old_product_id,
        "new_product_id": alt_product_id,
        "new_product_name": alt_product_name,
        "quantity": old_quantity,
        "new_unit_price_try": alt_product_price,
        "applied_discount_pct": applied_discount,
    }
    output = {"success": True, "quote_id": params.quote_id, **quote_delta}

    duration_ms = int((time.monotonic() - start_time) * 1000)
    await _log_tool_call(
        db, session_id, "replace_with_alternative", params.model_dump(), output,
        ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
    )
    await db.commit()
    return output