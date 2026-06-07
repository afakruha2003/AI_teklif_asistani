from __future__ import annotations

import time
import uuid
import logging
import re
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

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "var", "mı", "mi", "mu", "mü", "mı?", "mi?", "mu?", "mü?",
    "ekler", "misin", "misin?", "ekleyebilir", "ekleyebilir?",
    "nedir", "nedir?", "nasıl", "nasıl?", "kaç", "ne", "bir",
    "için", "ile", "ve", "veya", "ya", "da", "de", "bu", "şu",
    "altı", "üstü", "altında", "üstünde", "aşağı", "yukarı",
    "öner", "önerir", "önerin", "tavsiye", "istiyorum", "istiyorum.",
    "lütfen", "acaba", "bana", "benim",
    "tl", "try", "lira", "₺", "fiyat", "fiyatlı", "fiyatı",
    "ürün", "ürünler", "ürününü", "ürünü",
    "üzerinde", "üstünde",
    "ucuz", "ekonomik", "uygun", "uygun fiyatlı",
    "hizmetleri", "hizmeti", "hizmet", "nelerdir", "neler",
}

_NUMBER_RE = re.compile(r"^\d+([.,]\d+)?$")

SPECIAL_PHRASES = {
    "el terminali": "elterminali",
    "el terminal": "elterminali",
    "el terminalleri": "elterminali",
    "hand terminal": "elterminali",
    "mobil terminal": "elterminali",
    "pos cihazı": "elterminali",
    "pos cihazi": "elterminali",
    "satış terminali": "elterminali",
    "satis terminali": "elterminali",
    "barkod okuyucu": "barkodokuyucu",
    "barkod okuyucular": "barkodokuyucu",
    "barcode scanner": "barkodokuyucu",
    "kablosuz okuyucu": "barkodokuyucu",
    "qr okuyucu": "barkodokuyucu",
    "scanner": "barkodokuyucu",
    "etiket yazıcı": "etiketyazici",
    "etiket yazici": "etiketyazici",
    "label printer": "etiketyazici",
    "fiş yazıcı": "fisyazici",
    "fis yazici": "fisyazici",
    "receipt printer": "fisyazici",
    "termal yazıcı": "fisyazici",
    "termal yazici": "fisyazici",
    "yazılım lisansı": "yazilim",
    "yazilim lisansi": "yazilim",
    "stok yazılımı": "yazilim",
    "stok yazilimi": "yazilim",
    "depo yazılımı": "yazilim",
    "depo yazilimi": "yazilim",
    "software license": "yazilim",
    "şarj adaptörü": "sarj",
    "sarj adaptoru": "sarj",
    "usb c şarj": "usbcsarj",
    "silikon kılıf": "kilif",
    "silikon kilif": "kilif",
    "koruyucu kılıf": "kilif",
    "koruyucu kilif": "kilif",
    "yedek batarya": "batarya",
    "kurulum hizmeti": "kurulum",
    "yerinde kurulum": "kurulum",
    "acil kurulum": "acilkurulum",
    "installation service": "kurulum",
}

CATEGORY_KEYWORDS = {
    "pos_terminal": [
        "el terminali", "el terminal", "elterminali", "terminal",
        "pos", "el terminalleri", "hand terminal", "mobil terminal",
        "pos cihazı", "pos cihazi", "satış terminali", "satis terminali",
        "android terminal", "wifi terminal", "4g terminal", "dokunmatik terminal"
    ],
    "barcode_scanner": [
        "barkod okuyucu", "barkod", "okuyucu", "scanner",
        "barkod_okuyucu", "kablosuz okuyucu", "qr okuyucu",
        "barcode scanner", "1d scanner", "2d scanner", "kablolu okuyucu",
        "endüstriyel okuyucu", "endustriyel okuyucu", "rugged scanner"
    ],
    "label_printer": [
        "etiket yazıcı", "etiket", "label printer", "etiket_yazici",
        "barkod etiket", "etiket yazici", "etiket makinesi"
    ],
    "receipt_printer": [
        "fiş yazıcı", "fis yazici", "receipt printer", "termal yazıcı",
        "termal yazici", "fiş makinesi", "fis makinesi"
    ],
    "software": [
        "yazılım", "yazilim", "lisans", "software", "modül", "modul",
        "stok yazılımı", "depo yazılımı", "lisans anahtarı",
        "stok programı", "depo programı"
    ],
    "accessory": [
        "aksesuar", "şarj", "kılıf", "kilif", "batarya", "adaptör",
        "usb-c", "sarj", "koruyucu", "yedek", "şarj aleti", "sarj aleti"
    ],
    "service": [
        "kurulum", "servis", "hizmet", "service", "destek",
        "teknik destek", "kurulum hizmeti", "yerinde kurulum"
    ],
    "bundle": [
        "kit", "paket", "bundle", "set", "demo", "başlangıç seti",
        "depo kiti", "saha kiti"
    ],
}

# Default query placeholder — when this is the only query, skip token scoring
_DEFAULT_QUERY = "ürün"


def _normalize(text: str) -> str:
    return (
        text
        .replace("ğ", "g").replace("ü", "u").replace("ş", "s")
        .replace("ı", "i").replace("ö", "o").replace("ç", "c")
        .replace(" ", "")
    )


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    for phrase, replacement in SPECIAL_PHRASES.items():
        if phrase in text:
            text = text.replace(phrase, replacement)
    text = text.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ç", "c")
    text = text.replace("_", " ")
    tokens = text.split()
    result = []
    for t in tokens:
        clean = t.strip("?.!,;:()")
        if not clean:
            continue
        if clean in _STOPWORDS:
            continue
        if _NUMBER_RE.match(clean):
            continue
        result.append(clean)
    if not result:
        result = [w for w in text.split() if len(w) > 2]
    return result


def _score_product(p: Product, tokens: list[str]) -> int:
    if not tokens:
        return 1

    name_lower = p.name.lower()
    desc_lower = (p.description or "").lower()
    category_lower = p.category.lower()

    aliases = p.aliases
    if isinstance(aliases, dict):
        tr_aliases = [a.lower() for a in aliases.get("tr", [])]
    elif isinstance(aliases, list):
        tr_aliases = [a.lower() for a in aliases]
    else:
        tr_aliases = []

    tags_lower = [t.lower() for t in (p.tags or [])]

    name_norm = _normalize(name_lower)
    category_norm = _normalize(category_lower)

    score = 0
    for token in tokens:
        token_norm = _normalize(token)

        for cat, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if token_norm == _normalize(keyword) and _normalize(cat) == category_norm:
                    score += 50
                    break

        if token in name_lower:
            score += 10
        elif token_norm in name_norm:
            score += 8

        token_parts = token.replace("_", " ").split()
        name_parts = name_lower.split()
        for part in token_parts:
            if part in name_parts:
                score += 5
            for name_part in name_parts:
                if part in name_part or name_part in part:
                    score += 3

        if len(token_parts) > 1:
            if all(any(part in np or np in part for np in name_parts) for part in token_parts):
                score += 15

        if token in desc_lower:
            score += 3
        elif token_norm in _normalize(desc_lower):
            score += 2

        for alias in tr_aliases:
            if token in alias:
                score += 8
                break
            elif token_norm in _normalize(alias):
                score += 5
                break

        for tag in tags_lower:
            if token in tag:
                score += 5
                break
            elif token_norm in _normalize(tag):
                score += 3
                break

    return score


def detect_category_from_query(query: str) -> Optional[str]:
    query_norm = _normalize(query.lower())
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if _normalize(keyword) in query_norm:
                return category
    return None


def extract_price_limit_from_query(query: str) -> Optional[float]:
    query_lower = query.lower()
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)\s*(?:altında|altı|alti)",
        r"(?:altında|altı|alti)\s*(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)",
        r"max\s*(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)",
        r"maksimum\s*(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)",
        r"(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)\s*(?:ve altı|ve alti)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_str = match.group(1).replace(",", "").replace(".", "")
            try:
                return float(price_str)
            except ValueError:
                pass
    turkish_numbers = {
        "yüz": 100, "ikiyüz": 200, "üçyüz": 300, "dörtyüz": 400, "beşyüz": 500,
        "altıyüz": 600, "yediyüz": 700, "sekizyüz": 800, "dokuzyüz": 900,
        "bin": 1000, "ikibin": 2000, "üçbin": 3000, "dörtbin": 4000, "beşbin": 5000,
        "onbin": 10000,
    }
    for word, value in turkish_numbers.items():
        if word in query_lower and ("tl" in query_lower or "lira" in query_lower):
            return float(value)
    return None


def _clean_query(query: str) -> str:
    for token in ("var mı?", "var mi?", "ekler misin?", "ekler misin",
                  "ekleyebilir misin?", "ekleyebilir misin", "?", "."):
        query = query.replace(token, "")
    return " ".join(query.split()).strip()


def _score_knowledge(e: KnowledgeEntry, tokens: list[str]) -> int:
    if not tokens:
        return 1
    title_lower = e.title.lower()
    content_lower = (getattr(e, "content", None) or getattr(e, "body", None) or "").lower()
    tags_lower = [t.lower() for t in (e.tags or [])]
    score = 0
    for token in tokens:
        token_norm = _normalize(token)
        if token_norm in _normalize(title_lower):
            score += 10
        if token_norm in _normalize(content_lower):
            score += 5
        if any(token_norm in _normalize(t) for t in tags_lower):
            score += 7
    return score


def _serialize_product(p: Product) -> dict:
    aliases = p.aliases
    if isinstance(aliases, dict):
        tr_aliases = aliases.get("tr", [])
    elif isinstance(aliases, list):
        tr_aliases = aliases
    else:
        tr_aliases = []
    return {
        "id": p.id,
        "name": p.name,
        "name_tr": p.name,
        "description": p.description,
        "category": p.category,
        "price_try": float(p.price_try),
        "stock": p.stock,
        "sku": p.sku,
        "aliases": tr_aliases,
        "tags": p.tags or [],
        "is_active": p.is_active,
        "alternative_product_id": p.alternative_product_id,
        "substitute_product_ids": [],
        "min_order_qty": 1,
        "delivery_days": 3,
        "warranty_months": 24,
    }


def _serialize_knowledge(e: KnowledgeEntry) -> dict:
    body = getattr(e, "content", None) or getattr(e, "body", None) or ""
    return {
        "knowledge_id": e.id,
        "topic": getattr(e, "topic", e.category),
        "title": e.title,
        "content": body,
        "category": e.category,
        "tags": e.tags or [],
        "applies_to": getattr(e, "applies_to", []),
        "source": getattr(e, "source", None),
    }


def _serialize_quote_item(item: QuoteItem, product_name: Optional[str]) -> dict:
    qty = item.quantity
    unit = float(item.unit_price_try)
    disc = float(item.discount_pct)
    status_val = item.status.value if hasattr(item.status, "value") else item.status
    return {
        "id": item.id,
        "item_id": item.id,
        "product_id": item.product_id,
        "product_name": product_name,
        "sku": None,
        "quantity": qty,
        "unit_price_try": unit,
        "discount_pct": disc,
        "line_total_try": round(qty * unit * (1 - disc / 100), 2),
        "status": status_val,
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
        "id": quote.id,
        "quote_id": quote.id,
        "customer_id": quote.customer_id,
        "status": quote.status,
        "items": serialized_items,
        "active_items_count": len(active_items),
        "total_try": round(total_amount, 2),
    }


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
    quote_products: List[str] = None,
    sku: str = None,
) -> float:
    rule_stmt = (
        select(PriceRule)
        .where(
            PriceRule.is_active == True,
            or_(PriceRule.segment == segment, PriceRule.segment == None),
            or_(PriceRule.product_id == product_id, PriceRule.product_id == None),
            or_(
                func.lower(PriceRule.category) == category.lower(),
                PriceRule.category == None,
            ),
        )
        .order_by(PriceRule.priority.desc())
    )
    result = await db.execute(rule_stmt)
    rules = list(result.scalars().all())

    highest_discount = 0.0
    for rule in rules:
        min_qty = getattr(rule, "min_quantity", 1)
        if quantity < min_qty:
            continue
        condition = getattr(rule, "condition", None) or getattr(rule, "condition_text", "") or ""
        if "partner" in condition.lower() and "category_qty >= 3" in condition.lower():
            if segment.lower() == "partner":
                highest_discount = max(highest_discount, float(rule.discount_pct))
        elif "accessory" in condition.lower() and "product_qty >= 5" in condition.lower():
            if category.lower() == "accessory" and quantity >= 5:
                highest_discount = max(highest_discount, float(rule.discount_pct))
        elif "bundle" in condition.lower() or category.lower() == "bundle":
            return 0.0
        elif "software" in condition.lower() and "prd-sw-520" in condition.lower():
            if quote_products and "PRD-SW-520" in quote_products and "PRD-SW-530" in quote_products:
                highest_discount = max(highest_discount, float(rule.discount_pct))
        elif "plus" in condition.lower() and "product_qty >= 4" in condition.lower():
            if sku and "PLUS" in sku.upper() and quantity >= 4:
                highest_discount = max(highest_discount, float(rule.discount_pct))
        else:
            if quantity >= min_qty:
                highest_discount = max(highest_discount, float(rule.discount_pct))
    return highest_discount


async def _safe_rollback(db: AsyncSession) -> None:
    """Safe rollback that handles async properly."""
    try:
       
        if db.in_transaction():
            await db.rollback()
        await db.expire_all()
    except Exception as e:
        logger.warning(f"Rollback error (ignored): {e}")


async def search_products(
    db: AsyncSession,
    params: SearchProductsInput,
    session_id: str,
    sequence_num: int = 0,
    skip_logging: bool = False,
) -> Dict[str, Any]:
    
    start_time = time.monotonic()

    try:
        search_query = params.query or ""
        if not search_query.strip():
            search_query = _DEFAULT_QUERY

        effective_price_limit = params.max_price_try
        if effective_price_limit is None:
            effective_price_limit = extract_price_limit_from_query(search_query)

        detected_category = params.category
        if not detected_category:
            detected_category = detect_category_from_query(search_query)

        products = []

        # FIX: when category + price limit provided, fetch all in category first,
        # then apply price filter — but always respect in_stock_only
        if detected_category and effective_price_limit:
            stmt_no_limit = select(Product).where(
                Product.is_active == True,
                func.lower(Product.category) == detected_category.lower(),
            )
            if params.in_stock_only:
                stmt_no_limit = stmt_no_limit.where(Product.stock > 0)
            result_no_limit = await db.execute(stmt_no_limit.limit(200))
            all_category_products = list(result_no_limit.scalars().all())
            if all_category_products:
                products = [p for p in all_category_products if p.price_try <= effective_price_limit]

        if not products:
            stmt = select(Product).where(Product.is_active == True)
            if effective_price_limit is not None:
                stmt = stmt.where(Product.price_try <= effective_price_limit)
            if detected_category:
                stmt = stmt.where(func.lower(Product.category) == detected_category.lower())
            if params.in_stock_only:
                stmt = stmt.where(Product.stock > 0)
            result = await db.execute(stmt.limit(200))
            products = list(result.scalars().all())

        # FIX: Only apply token scoring when there's a meaningful query
        # (not just the default placeholder). This prevents filtering out
        # valid products when user only specifies category/price params.
        is_meaningful_query = (
            search_query
            and search_query.strip()
            and search_query.strip() != _DEFAULT_QUERY
        )

        if is_meaningful_query and products:
            tokens = _tokenize(_clean_query(search_query))
            if tokens:
                scored: list[tuple[Product, int]] = [
                    (p, _score_product(p, tokens)) for p in products
                ]
                scored = [(p, s) for p, s in scored if s > 0]
                scored.sort(key=lambda x: x[1], reverse=True)
                products = [p for p, _ in scored[: params.limit]] if scored else []
            else:
                products = products[: params.limit]
        else:
            # No meaningful query — just return all filtered products up to limit
            products = products[: params.limit]

        if params.tags and products:
            target = [t.lower() for t in params.tags]
            products = [p for p in products if any(t.lower() in target for t in (p.tags or []))]

        serialized = [_serialize_product(p) for p in products]
        output: Dict[str, Any] = {
            "products": serialized,
            "count": len(serialized),
            "detected_category": detected_category,
            "original_query": search_query,
            "price_limit_used": effective_price_limit,
        }

        if not products and effective_price_limit and effective_price_limit > 0:
            category_to_search = detected_category or params.category

            if category_to_search:
                stmt_same = select(Product).where(
                    Product.is_active == True,
                    Product.stock > 0,
                    func.lower(Product.category) == category_to_search.lower(),
                    Product.price_try > effective_price_limit,
                ).order_by(Product.price_try.asc()).limit(5)
                result_same = await db.execute(stmt_same)
                same_cat = list(result_same.scalars().all())
                if same_cat:
                    min_price = min(p.price_try for p in same_cat)
                    output["suggestions"] = {
                        "type": "same_category",
                        "category": category_to_search,
                        "message": f"{effective_price_limit:,.0f} TL bütçenizle uygun ürün bulunamadı.",
                        "products": [_serialize_product(p) for p in same_cat],
                        "price_limit": effective_price_limit,
                        "min_available_price": min_price,
                        "price_difference": round(min_price - effective_price_limit, 2),
                        "suggestion": f"Bütçenizi {min_price:,.0f} TL'ye çıkarmanızı öneririm.",
                    }

                if "suggestions" not in output:
                    stmt_all = select(Product).where(
                        Product.is_active == True,
                        Product.stock > 0,
                        func.lower(Product.category) == category_to_search.lower(),
                    ).order_by(Product.price_try.asc()).limit(5)
                    result_all = await db.execute(stmt_all)
                    all_cat = list(result_all.scalars().all())
                    if all_cat:
                        min_price = min(p.price_try for p in all_cat)
                        output["suggestions"] = {
                            "type": "category_info",
                            "category": category_to_search,
                            "message": f"En ucuz ürün {min_price:,.0f} TL'dir.",
                            "products": [_serialize_product(p) for p in all_cat],
                            "min_available_price": min_price,
                        }

            if "suggestions" not in output:
                stmt_nearby = select(Product).where(
                    Product.is_active == True,
                    Product.stock > 0,
                    Product.price_try > effective_price_limit,
                    Product.price_try <= effective_price_limit * 2,
                ).order_by(Product.price_try.asc()).limit(5)
                result_nearby = await db.execute(stmt_nearby)
                nearby = list(result_nearby.scalars().all())
                if nearby:
                    output["suggestions"] = {
                        "type": "nearby_price",
                        "message": f"{effective_price_limit:,.0f} TL altında ürün bulunamadı.",
                        "products": [_serialize_product(p) for p in nearby],
                        "price_limit": effective_price_limit,
                        "min_available_price": min(p.price_try for p in nearby),
                    }

        if not products and not effective_price_limit:
            stmt_top = select(Product).where(
                Product.is_active == True,
                Product.stock > 0,
            ).order_by(Product.price_try.asc()).limit(params.limit)
            result_top = await db.execute(stmt_top)
            top_products = list(result_top.scalars().all())
            if top_products:
                output["products"] = [_serialize_product(p) for p in top_products]
                output["count"] = len(top_products)
                output["message"] = "En uygun fiyatlı ürünler:"

        duration_ms = int((time.monotonic() - start_time) * 1000)
        if not skip_logging:
            await _log_tool_call(
                db, session_id, "search_products", params.model_dump(), output,
                ToolCallStatus.success, None, sequence_num, duration_ms,
            )
            await db.commit()
        return output

    except Exception as e:
        logger.error(f"search_products error: {e}")
        await _safe_rollback(db)
        return {"products": [], "count": 0, "error": str(e)}


async def get_knowledge_entries(
    db: AsyncSession,
    params: GetKnowledgeInput,
    session_id: str,
    sequence_num: int = 0,
    skip_logging: bool = False,
) -> Dict[str, Any]:
    
    start_time = time.monotonic()

    try:
        search_query = params.query or ""
        if not search_query.strip():
            search_query = "bilgi"

        stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
        if hasattr(params, "topic") and params.topic:
            stmt = stmt.where(KnowledgeEntry.topic == params.topic)
        if params.category:
            stmt = stmt.where(func.lower(KnowledgeEntry.category) == params.category.lower())

        result = await db.execute(stmt.limit(100))
        entries: List[KnowledgeEntry] = list(result.scalars().all())

        if search_query:
            tokens = _tokenize(search_query)
            if tokens:
                scored = [(e, _score_knowledge(e, tokens)) for e in entries]
                scored = [(e, s) for e, s in scored if s > 0]
                scored.sort(key=lambda x: x[1], reverse=True)
                entries = [e for e, _ in scored[: params.limit]]
            else:
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

    except Exception as e:
        await _safe_rollback(db)
        return {"knowledge_entries": [], "count": 0, "error": str(e)}


async def get_quote(
    db: AsyncSession,
    params: GetQuoteInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    
    start_time = time.monotonic()

    try:
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

    except Exception as e:
        await _safe_rollback(db)
        return {"error": str(e)}


async def add_to_quote(
    db: AsyncSession,
    params: Any,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    
    start_time = time.monotonic()

    try:
        # FIX: Check idempotency BEFORE any DB mutation.
        # If duplicate found, return cached result WITHOUT logging again
        # (logging again causes a UNIQUE constraint violation on idempotency_key).
        if params.idempotency_key:
            existing_log = await db.execute(
                select(ToolCallLog).where(
                    ToolCallLog.idempotency_key == params.idempotency_key,
                    ToolCallLog.tool_name == "add_to_quote",
                )
            )
            existing = existing_log.scalar_one_or_none()
            if existing:
                output = {
                    "idempotent": True,
                    "message": "Duplicate request ignored",
                    "previous_result": existing.output_data,
                }
                # Do NOT log again — would cause UNIQUE constraint violation
                return output

        if not params.quote_id or params.quote_id in ("null", "None"):
            stmt = select(Quote).where(Quote.session_id == session_id).order_by(Quote.id.desc())
            quote_res = await db.execute(stmt)
            existing_quote = quote_res.scalar_one_or_none()
            if existing_quote:
                params.quote_id = existing_quote.id
            else:
                new_quote = Quote(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    customer_id=getattr(params, "customer_id", None),
                    status="draft",
                )
                db.add(new_quote)
                await db.flush()
                params.quote_id = new_quote.id

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
                QuoteItem.status == "active",
            )
        )
        curr_item = existing_item_result.scalar_one_or_none()

        curr_item_id = curr_item.id if curr_item else None
        curr_item_qty = curr_item.quantity if curr_item else 0
        simulated_qty = params.quantity + curr_item_qty

        quote_products_result = await db.execute(
            select(QuoteItem.product_id).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.status == "active",
            )
        )
        quote_products = list(quote_products_result.scalars().all())

        applied_discount = await _get_discount(
            db, product_id, product_category, segment, simulated_qty,
            quote_products, product.sku,
        )

        is_backorder = False
        if product_stock <= 0 or product_stock < params.quantity:
            if not params.allow_backorder:
                output = {
                    "error": "Product is out of stock or insufficient stock",
                    "rule_violated": "out_of_stock",
                    "product_id": product_id,
                    "current_stock": product_stock,
                }
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
            final_qty = simulated_qty
        else:
            new_item = QuoteItem(
                id=str(uuid.uuid4()),
                quote_id=params.quote_id,
                product_id=product_id,
                quantity=params.quantity,
                unit_price_try=product_price,
                discount_pct=applied_discount,
                status="active",
                is_backorder=is_backorder,
            )
            db.add(new_item)
            action = "item_added"
            item_id = new_item.id
            final_qty = params.quantity

        if not is_backorder:
            product.stock -= params.quantity

        quote_delta = {
            "action": action,
            "item_id": item_id,
            "product_id": product_id,
            "product_name": product_name,
            "new_quantity": final_qty,
            "unit_price_try": product_price,
            "applied_discount_pct": applied_discount,
        }
        output = {
            "success": True,
            "quote_id": params.quote_id,
            "action": action,
            "item_id": item_id,
            "product_id": product_id,
            "product_name": product_name,
            "new_quantity": final_qty,
            "unit_price_try": product_price,
            "applied_discount_pct": applied_discount,
        }

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(
            db, session_id, "add_to_quote", params.model_dump(), output,
            ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
            idempotency_key=params.idempotency_key,
        )
        await db.commit()
        return output

    except Exception as e:
        await _safe_rollback(db)
        return {"error": str(e)}


async def update_quote_item(
    db: AsyncSession,
    params: UpdateQuoteItemInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    
    start_time = time.monotonic()

    try:
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
                output = {
                    "error": "Product is out of stock, cannot modify quantity",
                    "rule_violated": "out_of_stock",
                }
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                                     ToolCallStatus.error, None, sequence_num, duration_ms)
                await db.commit()
                return output

            quote = await db.get(Quote, params.quote_id)
            customer_id = quote.customer_id if quote else None
            segment = await _get_customer_segment(db, customer_id)

            quote_products_result = await db.execute(
                select(QuoteItem.product_id).where(
                    QuoteItem.quote_id == params.quote_id,
                    QuoteItem.status == "active",
                )
            )
            quote_products = list(quote_products_result.scalars().all())

            applied_discount = await _get_discount(
                db, item_product_id, product_category, segment, params.quantity,
                quote_products, product.sku if product else None,
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
        output = {
            "success": True,
            "quote_id": params.quote_id,
            "action": action,
            "item_id": params.item_id,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "applied_discount_pct": applied_discount,
        }

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(
            db, session_id, "update_quote_item", params.model_dump(), output,
            ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
        )
        await db.commit()
        return output

    except Exception as e:
        await _safe_rollback(db)
        return {"error": str(e)}


async def replace_with_alternative(
    db: AsyncSession,
    params: ReplaceWithAlternativeInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    
    start_time = time.monotonic()

    try:
        old_item = None
        old_product_id = None

        if params.item_id:
            old_item = await db.get(QuoteItem, params.item_id)
            if old_item:
                old_product_id = old_item.product_id

        if not old_item and hasattr(params, "from_product_id") and params.from_product_id:
            stmt = select(QuoteItem).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.product_id == params.from_product_id,
                QuoteItem.status == "active",
            ).order_by(QuoteItem.created_at.desc()).limit(1)
            result = await db.execute(stmt)
            old_item = result.scalar_one_or_none()
            if old_item:
                old_product_id = params.from_product_id

        if not old_item:
            output = {"error": "Item not found in active quote"}
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
        old_quantity = old_item.quantity
        old_unit_price = float(old_item.unit_price_try)
        old_product = await db.get(Product, old_product_id)

        alt_product_id = getattr(params, "alternative_product_id", None) or getattr(params, "to_product_id", None)

        if not alt_product_id and old_product:
            alt_product_id = old_product.alternative_product_id
            if not alt_product_id:
                stmt_alt = select(Product).where(
                    Product.is_active == True,
                    Product.stock > 0,
                    Product.category == old_product.category,
                    Product.id != old_product_id,
                    Product.price_try <= old_product.price_try * 1.2,
                ).order_by(Product.price_try.asc()).limit(1)
                result_alt = await db.execute(stmt_alt)
                auto_alt = result_alt.scalar_one_or_none()
                if auto_alt:
                    alt_product_id = auto_alt.id

        if not alt_product_id:
            output = {"error": "No suitable alternative product found"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        alt_product = await db.get(Product, alt_product_id)
        if not alt_product or not alt_product.is_active:
            output = {"error": "Alternative product not available"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        alt_product_price = float(alt_product.price_try)

        max_price = getattr(params, "max_price_try", None)
        if max_price is not None and alt_product_price > max_price:
            output = {"error": f"Alternative price ({alt_product_price}) exceeds limit ({max_price})"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        if alt_product.stock <= 0:
            output = {"error": "Alternative out of stock"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        quote = await db.get(Quote, params.quote_id)
        customer_id = quote.customer_id if quote else None
        segment = await _get_customer_segment(db, customer_id)

        quote_products_result = await db.execute(
            select(QuoteItem.product_id).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.status == "active",
            )
        )
        quote_products = list(quote_products_result.scalars().all())

        applied_discount = await _get_discount(
            db, alt_product_id, alt_product.category, segment, old_quantity,
            quote_products, alt_product.sku,
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

        # FIX: Use explicit enum value to avoid status comparison issues after commit
        old_item.status = QuoteItemStatus.replaced
        old_item.replaced_by_item_id = new_item_id

        alt_product.stock -= old_quantity

        quote_delta = {
            "action": "item_replaced",
            "old_item_id": old_item_id,
            "new_item_id": new_item_id,
            "old_product_id": old_product_id,
            "new_product_id": alt_product_id,
            "new_product_name": alt_product.name,
            "quantity": old_quantity,
            "old_price": old_unit_price,
            "new_price": alt_product_price,
            "price_difference": round(alt_product_price - old_unit_price, 2),
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

    except Exception as e:
        logger.error(f"replace_with_alternative error: {e}")
        await _safe_rollback(db)
        return {"error": str(e)}
