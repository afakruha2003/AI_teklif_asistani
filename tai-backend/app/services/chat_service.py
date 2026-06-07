from __future__ import annotations

import json
import uuid
import logging
import re
from typing import AsyncGenerator, Dict, Any, Optional, List

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

logger = logging.getLogger(__name__)

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Searches items matching criteria. If user asks by category, use category name as query. NEVER pass empty string as query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword. MUST NOT be empty. Use category name if no keyword."},
                    "category": {"type": "string", "description": "Filter by product category (optional)"},
                    "max_price_try": {"type": "number", "description": "Upper pricing limit in TRY"},
                    "in_stock_only": {"type": "boolean", "default": True},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
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
                    "query": {"type": "string", "description": "Search query. MUST NOT be empty."},
                    "category": {"type": "string", "description": "Filter by category (optional)"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
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
                    "quote_id": {"type": "string", "description": "The exact ID of the active target quote draft. NEVER invent a new UUID here."},
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
                    "quote_id": {"type": "string", "description": "The exact ID of the active target quote draft. NEVER invent a new UUID here."},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "description": "Exact item quantity requested by user. Default is 1.", "default": 1},
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
                    "quote_id": {"type": "string", "description": "The exact ID of the active target quote draft. NEVER invent a new UUID here."},
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
                    "quote_id": {"type": "string", "description": "The exact ID of the active target quote draft. NEVER invent a new UUID here."},
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

CRITICAL GROQ COMPATIBILITY RULES:
1. NEVER pass empty strings as parameter values. If a parameter is optional and you don't have a value, OMIT it entirely.
2. For search_products, ALWAYS provide a non-empty 'query' string. If user asks by category, use category name as query.
3. Example: User asks "500 TL altı el terminali öner" -> search_products(query="el terminali", max_price_try=500)
4. Do NOT use query="" (empty string) - this will cause an API error.

Operational Compliance Rules:
- Absolute Price Caps: If a maximum price limit is active, do not suggest or add products above it.
- Default Stock Rule: Do not recommend out-of-stock items (stock=0) unless user explicitly accepts wait.
- Citation Enforcement: MUST call get_knowledge_entries before answering policy questions.
- Aggregation Rule: Never duplicate item slots; increase quantity additively.
- Language Constraint: All responses must be in Turkish.
- Exact Product Match: Add ONLY the exact product requested. Do not add Plus variants unless explicitly requested.

CRITICAL RESPONSE RULES:
- After calling search_products, examine the actual products returned.
- If products found, list them with prices.
- If no products found within price limit, suggest increasing budget or show alternatives.
- Always check if search_products result has 'suggestions' key. If yes, use it to recommend alternatives.

CONVERSATION CONTEXT:
- Remember previous user questions and answers.
- If user asks for alternatives after a specific product, suggest from SAME category.
- Keep track of the last mentioned product category.

CRITICAL CATEGORY SEARCH RULES:
- "el terminali" -> ONLY search in pos_terminal category
- "barkod okuyucu" -> ONLY search in barcode_scanner category
- "yazıcı" -> search in label_printer and receipt_printer categories
- "yazılım" -> ONLY search in software category
- Do NOT mix categories unless user explicitly asks for alternatives.
"""

def _clean_tool_arguments(tool_calls_list: List[Any]) -> List[Any]:
    for tc in tool_calls_list:
        if not tc.function.arguments:
            continue
            
        try:
            args = json.loads(tc.function.arguments)
            if not isinstance(args, dict):
                continue
                
            cleaned = {}
            for k, v in args.items():
                if v == "" or v is None:
                    continue
                cleaned[k] = v
            
            if tc.function.name == "search_products":
                if "query" not in cleaned or cleaned.get("query") == "":
                    if "category" in cleaned and cleaned["category"]:
                        cleaned["query"] = cleaned["category"]
                    else:
                        cleaned["query"] = "urun"
                if "max_price_try" in cleaned and cleaned["max_price_try"] is None:
                    del cleaned["max_price_try"]
                if "limit" in cleaned and cleaned["limit"] is None:
                    del cleaned["limit"]
            
            if tc.function.name == "get_knowledge_entries":
                if "query" not in cleaned or cleaned.get("query") == "":
                    cleaned["query"] = "bilgi"
                if "limit" in cleaned and cleaned["limit"] is None:
                    del cleaned["limit"]
            
            if tc.function.name == "add_to_quote":
                if "quantity" not in cleaned or cleaned.get("quantity") is None:
                    cleaned["quantity"] = 1
                if "max_price_try" in cleaned and cleaned["max_price_try"] is None:
                    del cleaned["max_price_try"]
            
            tc.function.arguments = json.dumps(cleaned, ensure_ascii=False)
            
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            logger.debug(f"Error cleaning arguments for {tc.function.name}: {e}")
            continue
    
    return tool_calls_list

def _parse_turkish_number(text: str) -> float | None:
    _ONES = {
        "sifir": 0, "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5,
        "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
        "onbir": 11, "oniki": 12, "onuc": 13, "ondort": 14, "onbes": 15,
        "onalti": 16, "onyedi": 17, "onsekiz": 18, "ondokuz": 19,
        "yirmi": 20, "otuz": 30, "kirk": 40, "elli": 50,
        "altmis": 60, "yetmis": 70, "seksen": 80, "doksan": 90,
    }
    _MAGNITUDE = {"yuz": 100, "bin": 1000, "milyon": 1000000}
    _CURRENCY = {"tl", "try", "lira"}

    tokens = text.lower().split()
    if not any(t.strip("?!,") in _CURRENCY for t in tokens):
        return None

    cur_idx = next((i for i, t in enumerate(tokens) if t.strip("?!,") in _CURRENCY), -1)
    if cur_idx == -1:
        return None

    num_tokens = tokens[max(0, cur_idx - 6):cur_idx]
    total = 0.0
    current = 0.0

    for t in num_tokens:
        t = t.strip("?!,")
        if t in ("bucuk", "yarim"):
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

async def dispatch_tool(
    tool_name: str,
    tool_args: dict,
    db: AsyncSession,
    session_id: str,
    sequence_num: int,
    request: ChatRequest,
) -> dict:
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

async def stream_chat_llm(
    request: ChatRequest,
    db: AsyncSession,
    session_id: str,
    messages_list: list[dict],
    quote_id: str | None = None,
) -> AsyncGenerator[str, None]:
    from openai import AsyncOpenAI
    import asyncio

    logger.info(f"LLM STREAM START - Session: {session_id}, Quote: {quote_id}")
    logger.info(f"OpenAI Config: Model={settings.OPENAI_MODEL}, BaseURL={settings.OPENAI_BASE_URL}")
    logger.info(f"Previous messages count: {len(messages_list)}")

    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is missing in stream_chat_llm")
        raise ValueError("OPENAI_API_KEY is required for LLM mode")

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
    )

    messages: list[dict] = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]

    for msg in messages_list:
        if not msg.get("content"):
            continue
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})
        elif msg["role"] == "tool":
            continue
        else:
            messages.append({"role": msg["role"], "content": msg["content"]})

    logger.info(f"Loaded {len(messages)-1} previous messages into context")

    def has_category_in_query(query: str) -> bool:
        query_lower = query.lower()
        keywords = ["el terminali", "barkod", "yazici", "yazilim", "lisans", "aksesuar", "kurulum", "scanner", "printer", "terminal", "etiket"]
        return any(kw in query_lower for kw in keywords)

    def get_last_category_from_history(msgs: list[dict]) -> Optional[str]:
        category_map = {
            "el terminali": "pos_terminal", "terminal": "pos_terminal", "pos": "pos_terminal",
            "barkod": "barcode_scanner", "scanner": "barcode_scanner", "okuyucu": "barcode_scanner",
            "yazici": "label_printer", "printer": "label_printer", "etiket": "label_printer",
            "yazilim": "software", "lisans": "software",
            "aksesuar": "accessory", "sarj": "accessory",
            "kurulum": "service"
        }
        for msg in reversed(msgs):
            if msg["role"] == "user":
                content = msg["content"].lower()
                for kw, cat in category_map.items():
                    if kw in content:
                        logger.info(f"Found category '{cat}' from keyword '{kw}'")
                        return cat
        return None

    user_payload = request.message
    if quote_id:
        user_payload += f" [Quote ID: {quote_id}]"
    if request.max_price_try:
        user_payload += f" [Budget: {request.max_price_try} TRY]"

    if not has_category_in_query(request.message):
        last_cat = get_last_category_from_history(messages_list)
        if last_cat:
            cat_tr = {
                "pos_terminal": "el terminali", "barcode_scanner": "barkod okuyucu",
                "label_printer": "etiket yazici", "software": "yazilim",
                "accessory": "aksesuar", "service": "kurulum"
            }.get(last_cat, last_cat)
            user_payload += f" [Context: {cat_tr} kategorisinde ara]"
            logger.info(f"Added category context: {cat_tr}")

    messages.append({"role": "user", "content": user_payload})
    logger.info(f"User message: {user_payload[:150]}...")

    sequence_num = 0
    yield f"event: session_start\ndata: {json.dumps({'session_id': session_id, 'type': 'session_start', 'quote_id': quote_id})}\n\n"

    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"LLM Iteration {iteration}")

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
                stream=False,
            )
        except Exception as api_error:
            logger.error(f"API call failed: {api_error}")
            yield f"event: text_chunk\ndata: {json.dumps({'text': 'Uzgunum, servis su anda mesgul. Lutfen biraz sonra tekrar deneyin.', 'session_id': session_id})}\n\n"
            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'type': 'done'})}\n\n"
            return

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        msg_obj = choice.message
        full_content = msg_obj.content or ""
        tool_calls_list = msg_obj.tool_calls or []

        logger.info(f"Response - Finish: {finish_reason}, Content: {len(full_content)} chars, Tools: {len(tool_calls_list)}")

        if tool_calls_list:
            tool_calls_list = _clean_tool_arguments(tool_calls_list)

        if full_content:
            cleaned = re.sub(r'<function=[^>]+>', '', full_content)
            cleaned = re.sub(r'</function>', '', cleaned)
            cleaned = re.sub(r'\[\{"id":.*?"function":.*?\}\]', '', cleaned)
            cleaned = re.sub(r'\\n\\n', '\n\n', cleaned)

            if cleaned.strip():
                chunk_size = 100
                for i in range(0, len(cleaned), chunk_size):
                    chunk = cleaned[i:i+chunk_size]
                    yield f"event: text_chunk\ndata: {json.dumps({'text': chunk, 'session_id': session_id})}\n\n"
                    await asyncio.sleep(0.02)

        tool_calls_raw: dict[str, dict] = {}
        for i, tc in enumerate(tool_calls_list):
            tool_calls_raw[str(i)] = {
                "id": tc.id or f"call_{uuid.uuid4().hex[:8]}",
                "name": tc.function.name or "",
                "arguments": tc.function.arguments or "{}",
            }

        formatted_tool_calls: list[dict] = []
        if tool_calls_raw:
            for key in sorted(tool_calls_raw.keys(), key=int):
                val = tool_calls_raw[key]
                formatted_tool_calls.append({
                    "id": val["id"],
                    "type": "function",
                    "function": {"name": val["name"], "arguments": val["arguments"]},
                })

        if full_content or formatted_tool_calls:
            assistant_payload = {"role": "assistant", "content": full_content or None}
            if formatted_tool_calls:
                assistant_payload["tool_calls"] = formatted_tool_calls
            messages.append(assistant_payload)

            persisted = full_content if full_content else json.dumps(formatted_tool_calls, ensure_ascii=False)
            asst_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=persisted[:1000],
            )
            db.add(asst_msg)
            await db.commit()

        if not tool_calls_raw or finish_reason == "stop":
            logger.info("LLM completed")
            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'type': 'done'})}\n\n"
            return

        tool_results: list[dict] = []
        all_sources: list[dict] = []

        for key in sorted(tool_calls_raw.keys(), key=int):
            tc_data = tool_calls_raw[key]
            tool_name = tc_data["name"]

            try:
                tool_args = json.loads(tc_data["arguments"] or "{}")
            except json.JSONDecodeError:
                tool_args = {}

            if quote_id and "quote_id" in tool_args:
                if not tool_args["quote_id"] or tool_args["quote_id"] != quote_id:
                    tool_args["quote_id"] = quote_id

            sequence_num += 1
            yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name, 'input': tool_args, 'sequence': sequence_num, 'session_id': session_id})}\n\n"

            try:
                result = await dispatch_tool(tool_name, tool_args, db, session_id, sequence_num, request)
                logger.info(f"Tool {tool_name} executed")
            except Exception as tool_exc:
                logger.error(f"Tool {tool_name} error: {tool_exc}")
                await db.rollback()
                result = {"error": str(tool_exc)}

            if tool_name == "search_products":
                for p in result.get("products", []):
                    all_sources.append({"type": "product", "id": p["id"], "name": p.get("name", "")})
                if "suggestions" in result:
                    for p in result["suggestions"].get("products", []):
                        all_sources.append({"type": "product", "id": p["id"], "name": p.get("name", "")})
            elif tool_name == "get_knowledge_entries":
                for e in result.get("knowledge_entries", []):
                    all_sources.append({"type": "knowledge", "id": e["knowledge_id"], "name": e.get("title", "")})

            quote_delta = result.get("quote_delta") or (
                {k: v for k, v in result.items() if k in ("action", "item_id", "product_id", "new_quantity")}
                if result.get("success") else None
            )

            tool_result_data = {
                'tool': tool_name,
                'success': 'error' not in result,
                'quote_delta': quote_delta,
                'sequence': sequence_num,
                'session_id': session_id
            }

            if tool_name == "search_products":
                if "suggestions" in result:
                    tool_result_data["suggestions"] = result["suggestions"]
                if "products" in result:
                    tool_result_data["product_count"] = len(result["products"])
                if "detected_category" in result:
                    tool_result_data["detected_category"] = result["detected_category"]

            yield f"event: tool_result\ndata: {json.dumps(tool_result_data)}\n\n"

            tool_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="tool",
                content=json.dumps(result, ensure_ascii=False, default=str)[:2000],
            )
            db.add(tool_msg)
            await db.commit()

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc_data["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

        if all_sources:
            unique_sources = []
            seen_ids = set()
            for s in all_sources:
                if s["id"] not in seen_ids:
                    seen_ids.add(s["id"])
                    unique_sources.append(s)
            yield f"event: sources\ndata: {json.dumps({'sources': unique_sources, 'session_id': session_id})}\n\n"

        messages.extend(tool_results)
        await asyncio.sleep(0.1)

    logger.warning(f"Max iterations ({max_iterations}) reached")
    yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'type': 'done', 'warning': 'max_iterations_reached'})}\n\n"

async def stream_chat_fallback(
    request: ChatRequest,
    db: AsyncSession,
    session_id: str,
    quote_id: str | None = None,
) -> AsyncGenerator[str, None]:
    sequence_num = 0
    logger.warning(f"FALLBACK MODE ACTIVE - Session: {session_id}")

    yield f"event: session_start\ndata: {json.dumps({'session_id': session_id, 'type': 'session_start', 'quote_id': quote_id, 'mode': 'fallback'})}\n\n"

    active_quote_id = quote_id or request.quote_id
    normalized_msg = request.message.lower()
    response_parts: list[str] = []
    source_ids: list[str] = []
    all_sources: list[dict] = []

    is_add_query = any(w in normalized_msg for w in ["ekle", "add", "koy", "ilave"])
    is_quote_query = (not is_add_query) and any(w in normalized_msg for w in ["teklif", "quote", "sepet", "siparis", "durum", "goster", "listele", "icerik", "ne var"])

    is_product_query = (not is_quote_query) and (not is_add_query) and any(w in normalized_msg for w in [
        "urun", "okuyucu", "yazici", "terminal", "lisans", "kurulum", "barkod", "fiyat", "stok", "oneri", "tavsiye",
        "printer", "scanner", "device", "el terminali", "software", "yazilim", "hizmet", "servis", "service",
        "modul", "entegrasyon", "uygulama", "program"
    ])

    is_policy_query = any(w in normalized_msg for w in ["iade", "garanti", "teslimat", "politika", "kural", "uyumluluk", "nasil", "ne zaman", "kac gun", "sart", "kosul", "indirim"])

    effective_max_price = request.max_price_try
    if effective_max_price is None:
        price_match = re.search(r"(\d[\d.,]*)\s*(?:tl|try|lira)", normalized_msg)
        if price_match:
            try:
                effective_max_price = float(price_match.group(1).replace(",", "").replace(".", ""))
            except ValueError:
                pass
        if effective_max_price is None:
            effective_max_price = _parse_turkish_number(normalized_msg)

    if is_add_query and active_quote_id:
        quantity = 1
        turkish_numbers = {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5}
        for w, num in turkish_numbers.items():
            if w in normalized_msg:
                quantity = num
                break
        qty_match = re.search(r"(\d+)\s*(?:adet|tane)", normalized_msg)
        if qty_match:
            quantity = int(qty_match.group(1))

        sequence_num += 1
        try:
            search_res = await search_products(db, SearchProductsInput(query=request.message, limit=1), session_id, sequence_num, skip_logging=True)
        except Exception:
            search_res = {"products": []}

        products = search_res.get("products", [])
        if products:
            target_prod = products[0]
            sequence_num += 1
            yield f"event: tool_start\ndata: {json.dumps({'tool': 'add_to_quote', 'input': {'quote_id': active_quote_id, 'product_id': target_prod['id'], 'quantity': quantity}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
            try:
                add_res = await add_to_quote(db, AddToQuoteInput(quote_id=active_quote_id, product_id=target_prod["id"], quantity=quantity, allow_backorder=True), session_id, sequence_num)
            except Exception as e:
                add_res = {"error": str(e)}

            if "error" not in add_res:
                response_parts.append(f"**{target_prod['name']}** urununden {quantity} adet basariyla teklifinize eklendi.")
                try:
                    quote_now = await get_quote(db, GetQuoteInput(quote_id=active_quote_id), session_id, sequence_num)
                    if "error" not in quote_now:
                        response_parts.append(f"Guncel Teklif Toplami: **{quote_now.get('total_try', 0):,.0f} TRY**")
                except Exception:
                    pass
            else:
                response_parts.append(f"Teklife ekleme yapilirken bir hata olustu: {add_res.get('error')}")

            quote_delta = add_res.get("quote_delta") or ({"action": "add", "product_id": target_prod["id"], "new_quantity": quantity} if "error" not in add_res else None)
            yield f"event: tool_result\ndata: {json.dumps({'tool': 'add_to_quote', 'success': 'error' not in add_res, 'quote_delta': quote_delta, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        else:
            response_parts.append("Eklenecek uygun bir urun bulunamadi. Lutfen urun ismini net yazin.")

    elif is_quote_query and active_quote_id:
        sequence_num += 1
        yield f"event: tool_start\ndata: {json.dumps({'tool': 'get_quote', 'input': {'quote_id': active_quote_id}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        try:
            quote_result = await get_quote(db, GetQuoteInput(quote_id=active_quote_id), session_id, sequence_num)
        except Exception as e:
            quote_result = {"error": str(e)}

        if "error" not in quote_result:
            items = quote_result.get("items", [])
            total = quote_result.get("total_try", 0)
            if items:
                response_parts.append(f"Teklifinizde {len(items)} kalem bulunmaktadir (Toplam: {total:,.0f} TRY):")
                for item in items:
                    response_parts.append(f"- **{item.get('product_name', item.get('product_id', '?'))}** | Adet: {item.get('quantity', '?')} | Birim: {item.get('unit_price_try', 0):,.0f} TRY")
            else:
                response_parts.append("Teklifiniz henuz bos.")
        else:
            response_parts.append(f"Teklif bilgisi alinamadi: {quote_result.get('error')}")

        yield f"event: tool_result\ndata: {json.dumps({'tool': 'get_quote', 'success': 'error' not in quote_result, 'sequence': sequence_num, 'session_id': session_id})}\n\n"

    elif is_quote_query and not active_quote_id:
        response_parts.append("Aktif bir teklif oturumu bulunamadi. Lutfen once bir teklif olusturun.")

    if is_policy_query or (not is_product_query and not is_quote_query and not is_add_query):
        sequence_num += 1
        yield f"event: tool_start\ndata: {json.dumps({'tool': 'get_knowledge_entries', 'input': {'query': request.message}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        try:
            knowledge_result = await get_knowledge_entries(db, GetKnowledgeInput(query=request.message, limit=3), session_id, sequence_num, skip_logging=True)
        except Exception as e:
            knowledge_result = {"knowledge_entries": [], "error": str(e)}

        for entry in knowledge_result.get("knowledge_entries", []):
            kid = entry["knowledge_id"]
            source_ids.append(kid)
            all_sources.append({"type": "knowledge", "id": kid, "name": entry.get("title", "")})
            body = entry.get("content") or entry.get("body") or ""
            response_parts.append(f"**{entry['title']}**: {body}" if body else f"**{entry['title']}**")

        yield f"event: tool_result\ndata: {json.dumps({'tool': 'get_knowledge_entries', 'success': 'error' not in knowledge_result, 'count': len(knowledge_result.get('knowledge_entries', [])), 'sequence': sequence_num, 'session_id': session_id})}\n\n"

    if is_product_query:
        sequence_num += 1
        search_input = SearchProductsInput(query=request.message, max_price_try=effective_max_price, in_stock_only=True, limit=10)
        yield f"event: tool_start\ndata: {json.dumps({'tool': 'search_products', 'input': {'query': request.message, 'max_price_try': effective_max_price}, 'sequence': sequence_num, 'session_id': session_id})}\n\n"
        try:
            product_result = await search_products(db, search_input, session_id, sequence_num, skip_logging=True)
        except Exception as e:
            product_result = {"products": [], "error": str(e)}

        products = product_result.get("products", [])
        if products:
            price_note = f" ({effective_max_price:,.0f} TRY alti)" if effective_max_price else ""
            response_parts.append(f"İlgili urunler{price_note}:")
            for prod in products:
                pid = prod["id"]
                source_ids.append(pid)
                all_sources.append({"type": "product", "id": pid, "name": prod.get("name", "")})
                response_parts.append(f"- **{prod['name']}** | {prod['price_try']:,.0f} TRY | Stok: {prod['stock']}")
        else:
            if effective_max_price:
                try:
                    fallback_result = await search_products(db, SearchProductsInput(query=request.message, max_price_try=None, in_stock_only=True, limit=5), session_id, sequence_num, skip_logging=True)
                    fallback_products = fallback_result.get("products", [])
                except Exception:
                    fallback_products = []

                if fallback_products:
                    response_parts.append(f"{effective_max_price:,.0f} TRY altinda stokta uygun urun bulunamadi. En yakin alternatifler:")
                    for prod in fallback_products:
                        pid = prod["id"]
                        source_ids.append(pid)
                        all_sources.append({"type": "product", "id": pid, "name": prod.get("name", "")})
                        response_parts.append(f"- **{prod['name']}** | {prod['price_try']:,.0f} TRY | Stok: {prod['stock']}")
                else:
                    response_parts.append(f"Arama kriterlerinize uygun stokta urun bulunamadi ({effective_max_price:,.0f} TRY altinda).")
            else:
                response_parts.append("Arama kriterlerinize uygun stokta urun bulunamadi.")

        yield f"event: tool_result\ndata: {json.dumps({'tool': 'search_products', 'success': 'error' not in product_result, 'sequence': sequence_num, 'session_id': session_id})}\n\n"

    if all_sources:
        yield f"event: sources\ndata: {json.dumps({'sources': all_sources, 'session_id': session_id})}\n\n"

    if not response_parts:
        response_parts.append("Sorunuzu anlayamadim. Lutfen urun adi, kategori veya politika konusu belirterek tekrar sorun.")

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

    yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'type': 'done', 'mode': 'fallback', 'sources': unique_source_ids})}\n\n"

async def handle_chat_stream(
    request: ChatRequest,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    try:
        session: ChatSession | None = None

        if request.session_id:
            result = await db.execute(
                select(ChatSession)
                .where(ChatSession.id == request.session_id)
                .options(selectinload(ChatSession.messages))
            )
            session = result.scalar_one_or_none()

        if session is None:
            quote_id: str = request.quote_id or ""
            if not quote_id:
                from app.models.models import Quote as QuoteModel
                new_quote = QuoteModel(id=str(uuid.uuid4()), customer_id=request.customer_id)
                db.add(new_quote)
                await db.flush()
                quote_id = new_quote.id

            session = ChatSession(id=str(uuid.uuid4()), quote_id=quote_id, customer_id=request.customer_id)
            db.add(session)
            await db.flush()

        session_id_str: str = str(session.id)
        session_quote_id_str: str | None = str(session.quote_id) if session.quote_id else None

        loaded_messages = session.__dict__.get("messages") or []
        safe_messages_list: list[dict] = [{"role": m.role, "content": m.content} for m in loaded_messages]
        safe_messages_list.append({"role": "user", "content": request.message})

        user_msg = ChatMessage(id=str(uuid.uuid4()), session_id=session_id_str, role="user", content=request.message)
        db.add(user_msg)
        await db.commit()

        if not request.quote_id and session_quote_id_str:
            request = request.model_copy(update={"quote_id": session_quote_id_str})

        llm_available = settings.llm_enabled and bool(settings.OPENAI_API_KEY)

        logger.info(f"CHAT MODE - LLM_AVAILABLE: {llm_available}, Session: {session_id_str}, Quote: {session_quote_id_str}")

        if llm_available:
            logger.info("STARTING IN LLM MODE")
            yield f"event: mode\ndata: {json.dumps({'mode': 'llm', 'session_id': session_id_str})}\n\n"
            try:
                async for event in stream_chat_llm(request, db, session_id_str, safe_messages_list, session_quote_id_str):
                    yield event
            except Exception as e:
                logger.error(f"LLM ERROR: {type(e).__name__}: {e}", exc_info=True)
                logger.warning("FALLING BACK TO FALLBACK MODE")
                yield f"event: mode\ndata: {json.dumps({'mode': 'fallback', 'reason': 'llm_error', 'session_id': session_id_str})}\n\n"
                async for event in stream_chat_fallback(request, db, session_id_str, session_quote_id_str):
                    yield event
        else:
            logger.warning("STARTING IN FALLBACK MODE")
            yield f"event: mode\ndata: {json.dumps({'mode': 'fallback', 'session_id': session_id_str})}\n\n"
            async for event in stream_chat_fallback(request, db, session_id_str, session_quote_id_str):
                yield event

    except Exception as stream_exc:
        logger.error(f"STREAM EXCEPTION: {type(stream_exc).__name__}: {stream_exc}", exc_info=True)
        yield f"event: error\ndata: {json.dumps({'error': str(stream_exc), 'session_id': request.session_id if request.session_id else 'unknown'})}\n\n"

        