from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.models import ChatSession, ChatMessage
from app.schemas.schemas import (
    ChatRequest, SearchProductsInput, GetKnowledgeInput, GetQuoteInput,
    AddToQuoteInput, UpdateQuoteItemInput, ReplaceWithAlternativeInput,
)
from app.tools.tool_implementations import (
    search_products, get_knowledge_entries, get_quote,
    add_to_quote, update_quote_item, replace_with_alternative,
)


OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Searches items matching criteria like query strings, categories, maximum price limits, stock status, and system tags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword or alias"},
                    "category": {"type": "string", "description": "Filter by product category"},
                    "max_price_try": {"type": "number", "description": "Upper pricing limit in TRY"},
                    "in_stock_only": {"type": "boolean", "default": True},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_entries",
            "description": "Retrieves internal business rules, delivery info, warranty conditions, price rules, and fallback answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Retrieves the current state and list items of a specific business quote draft.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quote_id": {"type": "string"},
                },
                "required": ["quote_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_quote",
            "description": "Appends a product item to a specific quote draft or updates its target quantity if already present.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quote_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "default": 1},
                    "idempotency_key": {"type": "string"},
                    "max_price_try": {"type": "number"},
                    "allow_backorder": {"type": "boolean", "default": False},
                },
                "required": ["quote_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_quote_item",
            "description": "Modifies the active quantity of an item inside a quote draft. Setting quantity to 0 removes the item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quote_id": {"type": "string"},
                    "item_id": {"type": "string"},
                    "quantity": {"type": "integer"},
                },
                "required": ["quote_id", "item_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_with_alternative",
            "description": "Swaps a target quote item with a cross-referenced eligible alternative product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quote_id": {"type": "string"},
                    "item_id": {"type": "string"},
                    "alternative_product_id": {"type": "string"},
                    "max_price_try": {"type": "number"},
                },
                "required": ["quote_id", "item_id"],
            },
        },
    },
]

BASE_SYSTEM_PROMPT = """You are the enterprise sales engine for The Blue Red corporation.
The catalog includes barcode scanners, industrial hand terminals, thermal printers, corporate software licenses, and integration services.
Primary objectives involve answering requests accurately, recommending products, and maintaining quote draft parameters.

Operational Compliance Rules:
- Absolute Price Caps: If a maximum price limit is active, do not suggest or add products above it.
- Default Stock Rule: Do not recommend out-of-stock items (stock=0) unless explicitly instructed or backorder is allowed.
- Citation Enforcement: Append the respective 'knowledge_id' string whenever corporate guidelines are cited.
- Aggregation Rule: Never duplicate item slots for the same product; increase lines additively.
- Language Constraint: All public client communication must be executed in Turkish."""


# ─────────────────────────────────────────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────────────────────────────────────────

async def dispatch_tool(
    tool_name: str,
    tool_args: dict,
    db: AsyncSession,
    session_id: str,
    sequence_num: int,
    request: ChatRequest,
) -> dict:
    # Propagate global price cap to every relevant tool call
    if request.max_price_try is not None:
        if tool_name == "search_products" and "max_price_try" not in tool_args:
            tool_args["max_price_try"] = request.max_price_try
        if tool_name in ("add_to_quote", "replace_with_alternative") and "max_price_try" not in tool_args:
            tool_args["max_price_try"] = request.max_price_try

    if tool_name == "search_products":
        return await search_products(db, SearchProductsInput(**tool_args), session_id, sequence_num)
    elif tool_name == "get_knowledge_entries":
        return await get_knowledge_entries(db, GetKnowledgeInput(**tool_args), session_id, sequence_num)
    elif tool_name == "get_quote":
        return await get_quote(db, GetQuoteInput(**tool_args), session_id, sequence_num)
    elif tool_name == "add_to_quote":
        if request.idempotency_key and "idempotency_key" not in tool_args:
            tool_args["idempotency_key"] = request.idempotency_key
        return await add_to_quote(db, AddToQuoteInput(**tool_args), session_id, sequence_num)
    elif tool_name == "update_quote_item":
        return await update_quote_item(db, UpdateQuoteItemInput(**tool_args), session_id, sequence_num)
    elif tool_name == "replace_with_alternative":
        return await replace_with_alternative(db, ReplaceWithAlternativeInput(**tool_args), session_id, sequence_num)
    else:
        return {"error": f"Unknown tool reference: {tool_name}"}


# ─────────────────────────────────────────────────────────────────────────────
# LLM streaming path
# ─────────────────────────────────────────────────────────────────────────────

async def stream_chat_llm(
    request: ChatRequest,
    db: AsyncSession,
    session_id: str,
    messages_list: list[dict],
    quote_id: str | None = None,
) -> AsyncGenerator[str, None]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    # Build in-memory message history — never touch DB objects after commit
    messages: list[dict] = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]

    for msg in messages_list[:-1]:
        if not msg["content"]:
            continue
        if msg["role"] == "assistant" and msg["content"].startswith(("[", "{")):
            try:
                tool_calls = json.loads(msg["content"])
                messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
                continue
            except json.JSONDecodeError:
                pass
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_payload = request.message
    if request.max_price_try:
        user_payload += f" [Price Limit Threshold: {request.max_price_try} TRY]"
    if quote_id:
        user_payload += f" [Target Context Quote ID: {quote_id}]"
    messages.append({"role": "user", "content": user_payload})

    sequence_num = 0
    yield f"event: session_start\ndata: {json.dumps({'session_id': session_id, 'type': 'session_start', 'quote_id': quote_id})}\n\n"

    while True:
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            stream=True,
        )

        full_content = ""
        tool_calls_raw: dict[str, dict] = {}
        finish_reason = None

        async for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta

            if delta and delta.content:
                full_content += delta.content
                yield f"event: text_chunk\ndata: {json.dumps({'text': delta.content, 'session_id': session_id})}\n\n"

            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = str(tc.index)
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {
                            "id": tc.id or "",
                            "name": (tc.function.name or "") if tc.function else "",
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls_raw[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_raw[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_raw[idx]["arguments"] += tc.function.arguments

        # ── Build formatted tool-call list ────────────────────────────────
        formatted_tool_calls: list[dict] = []
        if tool_calls_raw:
            for key in sorted(tool_calls_raw.keys(), key=int):
                val = tool_calls_raw[key]
                formatted_tool_calls.append({
                    "id": val["id"],
                    "type": "function",
                    "function": {"name": val["name"], "arguments": val["arguments"]},
                })

        # ── Persist assistant turn ─────────────────────────────────────────
        # FIX: extract all primitives BEFORE commit so we never touch expired
        # ORM objects afterwards.
        if full_content or formatted_tool_calls:
            assistant_payload: dict = {
                "role": "assistant",
                "content": full_content or None,
            }
            if formatted_tool_calls:
                assistant_payload["tool_calls"] = formatted_tool_calls

            # Keep a plain-dict copy for messages history (safe post-commit)
            messages.append(dict(assistant_payload))

            persisted_content = (
                full_content if full_content else json.dumps(formatted_tool_calls)
            )
            asst_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=persisted_content,
            )
            db.add(asst_msg)
            await db.commit()
            # NOTE: we do NOT access asst_msg after this point — commit is done.

        # ── No tool calls → we're finished ────────────────────────────────
        if not tool_calls_raw or finish_reason == "stop":
            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'type': 'done'})}\n\n"
            break

        # ── Execute tool calls ─────────────────────────────────────────────
        tool_results: list[dict] = []
        all_sources: list[dict] = []

        for key in sorted(tool_calls_raw.keys(), key=int):
            tc_data = tool_calls_raw[key]
            tool_name = tc_data["name"]

            try:
                tool_args = json.loads(tc_data["arguments"] or "{}")
            except json.JSONDecodeError:
                tool_args = {}

            sequence_num += 1
            yield (
                f"event: tool_start\ndata: "
                f"{json.dumps({'tool': tool_name, 'input': tool_args, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
            )

            result = await dispatch_tool(
                tool_name, tool_args, db, session_id, sequence_num, request
            )

            # ── Extract sources before any further DB work ─────────────────
            if tool_name == "search_products":
                for p in result.get("products", []):
                    all_sources.append({"type": "product", "id": p["id"], "name": p.get("name", "")})
            elif tool_name == "get_knowledge_entries":
                for e in result.get("knowledge_entries", []):
                    all_sources.append({"type": "knowledge", "id": e["knowledge_id"], "name": e.get("title", "")})

            # ── Build quote_delta from result (primitives only) ────────────
            quote_delta: dict | None = result.get("quote_delta") or (
                {k: v for k, v in result.items() if k in ("action", "item_id", "product_id", "new_quantity")}
                if result.get("success")
                else None
            )

            yield (
                f"event: tool_result\ndata: "
                f"{json.dumps({'tool': tool_name, 'success': 'error' not in result, 'quote_delta': quote_delta, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
            )

            # ── Persist tool result as a chat message ──────────────────────
            # FIX: tool results were not persisted in the original code.
            tool_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="tool",
                content=json.dumps(result, ensure_ascii=False, default=str),
            )
            db.add(tool_msg)
            await db.commit()
            # Do NOT read tool_msg attributes after commit.

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc_data["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

        # Emit aggregated sources event after all tools in this round
        if all_sources:
            yield (
                f"event: sources\ndata: "
                f"{json.dumps({'sources': all_sources, 'session_id': session_id})}\n\n"
            )

        # Extend in-memory messages with tool results for next LLM turn
        messages.extend(tool_results)


# ─────────────────────────────────────────────────────────────────────────────
# Fallback (no-LLM) streaming path
# ─────────────────────────────────────────────────────────────────────────────

def _parse_turkish_number(text: str) -> float | None:
    """
    "onbir bin tl", "beş yüz lira", "iki buçuk bin try" gibi Türkçe
    yazılı sayıları float TRY değerine çevirir.
    Önce sayı kelimelerini rakama çevirir, ardından para birimi arar.
    Sonuç yoksa None döner.
    """
    _ONES = {
        "sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
        "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
        "onbir": 11, "oniki": 12, "onüç": 13, "ondört": 14, "onbeş": 15,
        "onaltı": 16, "onyedi": 17, "onsekiz": 18, "ondokuz": 19,
        "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50,
        "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90,
    }
    _MAGNITUDE = {"yüz": 100, "bin": 1000, "milyon": 1_000_000}
    _CURRENCY = {"tl", "try", "lira", "₺"}

    tokens = text.lower().split()

    if not any(t.strip("?.!,") in _CURRENCY for t in tokens):
        return None

    cur_idx = next(
        (i for i, t in enumerate(tokens) if t.strip("?.!,") in _CURRENCY), -1
    )
    if cur_idx == -1:
        return None

    num_tokens = tokens[max(0, cur_idx - 6): cur_idx]

    total = 0.0
    current = 0.0

    for t in num_tokens:
        t = t.strip("?.!,")
        if t in ("buçuk", "bucuk", "yarım"):
            # "buçuk" adds 0.5 to current BEFORE magnitude so that
            # "iki buçuk bin" → current=2.5 → *1000 = 2500
            current += 0.5
        elif t in _ONES:
            current += _ONES[t]
        elif t in _MAGNITUDE:
            mag = _MAGNITUDE[t]
            if current == 0:
                current = 1
            total += current * mag
            current = 0.0

    total += current
    return float(total) if total > 0 else None


async def stream_chat_fallback(
    request: ChatRequest,
    db: AsyncSession,
    session_id: str,
) -> AsyncGenerator[str, None]:
    import re

    sequence_num = 0
    yield (
        f"event: session_start\ndata: "
        f"{json.dumps({'session_id': session_id, 'type': 'session_start', 'mode': 'fallback'})}\n\n"
    )

    normalized_msg = request.message.lower()
    response_parts: list[str] = []
    source_ids: list[str] = []
    all_sources: list[dict] = []

    # ── Intent detection ───────────────────────────────────────────────────
    # FIX: Önce "Ekleme" niyetini özel olarak check ediyoruz
    is_add_query = any(word in normalized_msg for word in ["ekle", "add", "koy", "ilave"])
    
    # Eğer ekleme talebi DEĞİLSE normal teklif detay okumasıdır
    is_quote_query = (not is_add_query) and any(
        word in normalized_msg
        for word in [
            "teklif", "quote", "sepet", "sipariş", "durum", "göster",
            "listele", "içerik", "ne var", "neler var",
        ]
    )

    is_product_query = (not is_quote_query) and (not is_add_query) and any(
        word in normalized_msg
        for word in [
            "ürün", "okuyucu", "yazıcı", "terminal", "lisans", "kurulum",
            "barkod", "fiyat", "stok", "öneri", "tavsiye",
            "printer", "scanner", "device", "el terminali",
        ]
    )

    is_policy_query = any(
        word in normalized_msg
        for word in [
            "iade", "garanti", "teslimat", "politika", "kural", "uyumluluk",
            "nasıl", "ne zaman", "kaç gün", "şart", "koşul", "indirim",
        ]
    )

    effective_max_price = request.max_price_try
    if effective_max_price is None:
        price_match = re.search(r"(\d[\d.,]*)\s*(?:tl|try|lira|₺)", normalized_msg)
        if price_match:
            try:
                effective_max_price = float(price_match.group(1).replace(",", "").replace(".", ""))
            except ValueError:
                pass
        if effective_max_price is None:
            effective_max_price = _parse_turkish_number(normalized_msg)

    # ── 1. ADIM: Ekleme Senaryosu (ADD TO QUOTE) ───────────────────────────
    if is_add_query and request.quote_id:
        # Adet bulma: "2 adet", "5 tane" veya sadece sayı "3"
        quantity = 1
        qty_match = re.search(r"(\d+)\s*(?:adet|tane|line)?", normalized_msg)
        if qty_match:
            quantity = int(qty_match.group(1))

        # Önce sepete eklenecek ürünü veritabanında isminden bulalım
        sequence_num += 1
        search_res = await search_products(
            db, SearchProductsInput(query=request.message, limit=1), session_id, sequence_num, skip_logging=True
        )
        products = search_res.get("products", [])

        if products:
            target_prod = products[0]
            sequence_num += 1
            
            # Gerçek ekleme fonksiyonunu (tool) çağırıyoruz:
            yield (
                f"event: tool_start\ndata: "
                f"{json.dumps({'tool': 'add_to_quote', 'input': {'quote_id': request.quote_id, 'product_id': target_prod['id'], 'quantity': quantity}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
            )

            add_res = await add_to_quote(
                db, 
                AddToQuoteInput(
                    quote_id=request.quote_id, 
                    product_id=target_prod["id"], 
                    quantity=quantity,
                    allow_backorder=True
                ), 
                session_id, 
                sequence_num
            )

            if "error" not in add_res:
                response_parts.append(f"✅ **{target_prod['name']}** ürününden {quantity} adet başarıyla teklifinize eklendi.")
                # Güncel sepet özetini de hemen altına iliştirelim
                quote_now = await get_quote(db, GetQuoteInput(quote_id=request.quote_id), session_id, sequence_num)
                if "error" not in quote_now:
                    response_parts.append(f"Güncel Teklif Toplamı: **{quote_now.get('total_try', 0):,.0f} TRY**")
            else:
                response_parts.append(f"⚠️ Teklife ekleme yapılırken bir hata oluştu: {add_res.get('error')}")

            quote_delta = add_res.get("quote_delta") or ({"action": "add", "product_id": target_prod["id"], "new_quantity": quantity} if "error" not in add_res else None)
            yield (
                f"event: tool_result\ndata: "
                f"{json.dumps({'tool': 'add_to_quote', 'success': 'error' not in add_res, 'quote_delta': quote_delta, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
            )
        else:
            response_parts.append("Eklenecek uygun bir ürün bulunamadı. Lütfen ürün ismini net yazın.")

    # ── 2. ADIM: Normal Teklif Gösterimi ───────────────────────────────────
    elif is_quote_query and request.quote_id:
        sequence_num += 1
        yield (
            f"event: tool_start\ndata: "
            f"{json.dumps({'tool': 'get_quote', 'input': {'quote_id': request.quote_id}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        )
        quote_result = await get_quote(db, GetQuoteInput(quote_id=request.quote_id), session_id, sequence_num)
        if "error" not in quote_result:
            items = quote_result.get("items", [])
            total = quote_result.get("total_try", 0)
            if items:
                response_parts.append(f"Teklifinizde {len(items)} kalem bulunmaktadır (Toplam: {total:,.0f} TRY):")
                for item in items:
                    response_parts.append(f"- **{item.get('product_name', item.get('product_id', '?'))}** | Adet: {item.get('quantity', '?')} | Birim: {item.get('unit_price_try', 0):,.0f} TRY")
            else:
                response_parts.append("Teklifiniz henüz boş.")
        else:
            response_parts.append(f"Teklif bilgisi alınamadı: {quote_result.get('error')}")

        yield (
            f"event: tool_result\ndata: "
            f"{json.dumps({'tool': 'get_quote', 'success': 'error' not in quote_result, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        )

    elif is_quote_query and not request.quote_id:
        response_parts.append("Aktif bir teklif oturumu bulunamadı. Lütfen önce bir teklif oluşturun.")

    # ── 3. ADIM: Bilgi Havuzu Sorguları ────────────────────────────────────
    if is_policy_query or (not is_product_query and not is_quote_query and not is_add_query):
        sequence_num += 1
        yield (
            f"event: tool_start\ndata: "
            f"{json.dumps({'tool': 'get_knowledge_entries', 'input': {'query': request.message}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        )
        knowledge_result = await get_knowledge_entries(db, GetKnowledgeInput(query=request.message, limit=3), session_id, sequence_num, skip_logging=True)
        entries = knowledge_result.get("knowledge_entries", [])
        for entry in entries:
            kid = entry["knowledge_id"]
            source_ids.append(kid)
            all_sources.append({"type": "knowledge", "id": kid, "name": entry.get("title", "")})
            body = entry.get("content") or entry.get("body") or ""
            if body:
                response_parts.append(f"**{entry['title']}**: {body}")
            else:
                response_parts.append(f"**{entry['title']}**")

        yield (
            f"event: tool_result\ndata: "
            f"{json.dumps({'tool': 'get_knowledge_entries', 'success': True, 'count': len(entries), 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        )

    # ── 4. ADIM: Ürün Listeleme/Arama ──────────────────────────────────────
    if is_product_query:
        sequence_num += 1
        search_input = SearchProductsInput(query=request.message, max_price_try=effective_max_price, in_stock_only=True, limit=5)
        yield (
            f"event: tool_start\ndata: "
            f"{json.dumps({'tool': 'search_products', 'input': {'query': request.message, 'max_price_try': effective_max_price}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        )
        product_result = await search_products(db, search_input, session_id, sequence_num, skip_logging=True)
        products = product_result.get("products", [])
        if products:
            price_note = f" ({effective_max_price:,.0f} TRY altı)" if effective_max_price else ""
            response_parts.append(f"İlgili ürünler{price_note}:")
            for prod in products:
                pid = prod["id"]
                source_ids.append(pid)
                all_sources.append({"type": "product", "id": pid, "name": prod.get("name", "")})
                response_parts.append(f"- **{prod['name']}** | {prod['price_try']:,.0f} TRY | Stok: {prod['stock']}")
        else:
            if effective_max_price:
                fallback_result = await search_products(db, SearchProductsInput(query=request.message, max_price_try=None, in_stock_only=True, limit=3), session_id, sequence_num, skip_logging=True)
                fallback_products = fallback_result.get("products", [])
                if fallback_products:
                    response_parts.append(f"{effective_max_price:,.0f} TRY altında stokta uygun ürün bulunamadı. En yakın alternatifler:")
                    for prod in fallback_products:
                        pid = prod["id"]
                        source_ids.append(pid)
                        all_sources.append({"type": "product", "id": pid, "name": prod.get("name", "")})
                        response_parts.append(f"- **{prod['name']}** | {prod['price_try']:,.0f} TRY | Stok: {prod['stock']}")
                else:
                    response_parts.append(f"Arama kriterlerinize uygun stokta ürün bulunamadı ({effective_max_price:,.0f} TRY altında).")
            else:
                response_parts.append("Arama kriterlerinize uygun stokta ürün bulunamadı.")

        yield (
            f"event: tool_result\ndata: "
            f"{json.dumps({'tool': 'search_products', 'success': True, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        )

    # ── 5. ADIM: Çıktıları İletme ve Kapatma ────────────────────────────────
    if all_sources:
        yield (
            f"event: sources\ndata: "
            f"{json.dumps({'sources': all_sources, 'session_id': session_id})}\n\n"
        )

    if not response_parts:
        response_parts.append("Sorunuzu anlayamadım. Lütfen ürün adı, kategori veya politika konusu belirterek tekrar sorun.")

    full_response = "\n".join(response_parts)
    unique_source_ids = list(dict.fromkeys(source_ids))
    if unique_source_ids:
        full_response += f"\n\n_Kaynaklar: {', '.join(unique_source_ids)}_"

    buffer = ""
    for word in full_response.split(" "):
        buffer += word + " "
        if len(buffer) >= 60:
            yield f"event: text_chunk\ndata: {json.dumps({'text': buffer, 'session_id': session_id})}\n\n"
            buffer = ""
    if buffer.strip():
        yield f"event: text_chunk\ndata: {json.dumps({'text': buffer, 'session_id': session_id})}\n\n"

    yield (
        f"event: done\ndata: "
        f"{json.dumps({'session_id': session_id, 'type': 'done', 'mode': 'fallback', 'sources': unique_source_ids})}\n\n"
    )


async def handle_chat_stream(
    request: ChatRequest,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    try:
        # ── Resolve or create session ──────────────────────────────────────
        session: ChatSession | None = None

        if request.session_id:
            result = await db.execute(
                select(ChatSession)
                .where(ChatSession.id == request.session_id)
                .options(selectinload(ChatSession.messages))
            )
            session = result.scalar_one_or_none()

        if session is None:
            # Resolve or create quote
            quote_id: str = request.quote_id or ""
            if not quote_id:
                from app.models.models import Quote as QuoteModel

                new_quote = QuoteModel(
                    id=str(uuid.uuid4()),
                    customer_id=request.customer_id,
                )
                db.add(new_quote)
                await db.flush()
                quote_id = new_quote.id  # primitive str — safe after flush

            session = ChatSession(
                id=str(uuid.uuid4()),
                quote_id=quote_id,
                customer_id=request.customer_id,
            )
            db.add(session)
            await db.flush()

        # ── FIX: extract all primitives from ORM objects BEFORE commit ─────
        session_id_str: str = str(session.id)
        session_quote_id_str: str | None = str(session.quote_id) if session.quote_id else None

        # Convert message history to plain dicts now — do not keep ORM refs.
        # IMPORTANT: Use __dict__ to check whether 'messages' was actually
        # eagerly loaded (selectinload only runs for existing sessions).
        # Accessing session.messages on a *newly created* ChatSession would
        # trigger an implicit lazy-load, which raises MissingGreenlet in an
        # async context.
        loaded_messages = session.__dict__.get("messages") or []
        safe_messages_list: list[dict] = [
            {"role": m.role, "content": m.content}
            for m in loaded_messages
        ]

        # Append the new user message (plain dict first, ORM object to DB)
        safe_messages_list.append({"role": "user", "content": request.message})

        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id_str,
            role="user",
            content=request.message,
        )
        db.add(user_msg)

        # COMMIT ALL database operations BEFORE starting the generator
        await db.commit()
        # After this commit we only use *_str primitives and safe_messages_list

        # Propagate resolved quote_id into request for downstream tools
        if not request.quote_id and session_quote_id_str:
            request = request.model_copy(update={"quote_id": session_quote_id_str})

        # ── Delegate to LLM or fallback ────────────────────────────────────
        if settings.llm_enabled:
            async for event in stream_chat_llm(
                request, db, session_id_str, safe_messages_list, session_quote_id_str
            ):
                yield event
        else:
            async for event in stream_chat_fallback(request, db, session_id_str):
                yield event

    except Exception as stream_exc:
        import traceback

        print("\n" + "=" * 60)
        print("🚨 STREAM ERROR:")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60 + "\n")
        yield f"event: error\ndata: {json.dumps({'error': str(stream_exc)})}\n\n"

