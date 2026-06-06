import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import (
    Product, KnowledgeEntry, Quote, QuoteItem, ToolCallLog,
    QuoteItemStatus,
)
from app.schemas.schemas import (
    SearchProductsInput, GetKnowledgeInput, GetQuoteInput,
    AddToQuoteInput, UpdateQuoteItemInput, ReplaceWithAlternativeInput,
)
from app.tools.tool_implementations import (
    search_products, get_knowledge_entries, get_quote,
    add_to_quote, update_quote_item, replace_with_alternative,
)


SESSION_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_search_products_by_text(db: AsyncSession, product_in_stock: Product):
    result = await search_products(
        db,
        SearchProductsInput(query="kablosuz barkod"),
        SESSION_ID,
    )
    assert result["count"] >= 1
    ids = [p["id"] for p in result["products"]]
    assert product_in_stock.id in ids


@pytest.mark.asyncio
async def test_search_products_by_alias(db: AsyncSession, product_in_stock: Product):
    result = await search_products(
        db,
        SearchProductsInput(query="zebra okuyucu"),
        SESSION_ID,
    )
    assert any(p["id"] == product_in_stock.id for p in result["products"])


@pytest.mark.asyncio
async def test_search_products_by_category(db: AsyncSession, product_in_stock: Product):
    result = await search_products(
        db,
        SearchProductsInput(category="barkod_okuyucu"),
        SESSION_ID,
    )
    assert all(p["category"] == "barkod_okuyucu" for p in result["products"])


@pytest.mark.asyncio
async def test_get_knowledge_entries_by_query(db: AsyncSession, knowledge_return_policy: KnowledgeEntry):
    result = await get_knowledge_entries(
        db,
        GetKnowledgeInput(query="iade"),
        SESSION_ID,
    )
    assert result["count"] >= 1
    ids = [e["knowledge_id"] for e in result["knowledge_entries"]]
    assert knowledge_return_policy.id in ids


@pytest.mark.asyncio
async def test_get_knowledge_entries_returns_knowledge_id(db: AsyncSession, knowledge_return_policy: KnowledgeEntry):
    result = await get_knowledge_entries(
        db,
        GetKnowledgeInput(query="iade politika"),
        SESSION_ID,
    )
    for entry in result["knowledge_entries"]:
        assert "knowledge_id" in entry
        assert entry["knowledge_id"]


@pytest.mark.asyncio
async def test_get_quote_returns_correct_structure(db: AsyncSession, quote: Quote):
    result = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
    assert "quote_id" in result
    assert result["quote_id"] == quote.id
    assert "items" in result
    assert "total_try" in result


@pytest.mark.asyncio
async def test_get_quote_not_found(db: AsyncSession):
    result = await get_quote(db, GetQuoteInput(quote_id="nonexistent-id"), SESSION_ID)
    assert "error" in result


@pytest.mark.asyncio
async def test_add_to_quote_creates_item(db: AsyncSession, quote: Quote, product_in_stock: Product):
    result = await add_to_quote(
        db,
        AddToQuoteInput(
            quote_id=quote.id,
            product_id=product_in_stock.id,
            quantity=1,
        ),
        SESSION_ID,
    )
    assert result.get("success") is True
    assert result["action"] == "item_added"
    assert result["new_quantity"] == 1

    item_result = await db.execute(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.id,
            QuoteItem.product_id == product_in_stock.id,
            QuoteItem.status == QuoteItemStatus.active,
        )
    )
    item = item_result.scalar_one_or_none()
    assert item is not None
    assert item.quantity == 1


@pytest.mark.asyncio
async def test_update_quote_item_quantity(db: AsyncSession, quote_with_item: tuple):
    quote, item = quote_with_item
    result = await update_quote_item(
        db,
        UpdateQuoteItemInput(quote_id=quote.id, item_id=item.id, quantity=5),
        SESSION_ID,
    )
    assert result.get("success") is True
    assert result["new_quantity"] == 5
    assert result["action"] == "quantity_updated"

    await db.refresh(item)
    assert item.quantity == 5


@pytest.mark.asyncio
async def test_update_quote_item_quantity_zero_removes(db: AsyncSession, quote_with_item: tuple):
    quote, item = quote_with_item
    result = await update_quote_item(
        db,
        UpdateQuoteItemInput(quote_id=quote.id, item_id=item.id, quantity=0),
        SESSION_ID,
    )
    assert result.get("success") is True
    assert result["action"] == "item_removed"

    await db.refresh(item)
    assert item.status == QuoteItemStatus.removed


@pytest.mark.asyncio
async def test_replace_with_alternative(
    db: AsyncSession,
    quote: Quote,
    product_expensive: Product,
    product_cheap_alternative: Product,
):
    add_result = await add_to_quote(
        db,
        AddToQuoteInput(quote_id=quote.id, product_id=product_expensive.id, quantity=1),
        SESSION_ID,
    )
    assert add_result.get("success") is True
    item_id = add_result["item_id"]

    result = await replace_with_alternative(
        db,
        ReplaceWithAlternativeInput(
            quote_id=quote.id,
            item_id=item_id,
            alternative_product_id=product_cheap_alternative.id,
        ),
        SESSION_ID,
    )
    assert result.get("success") is True
    assert result["action"] == "item_replaced"
    assert result["new_product_id"] == product_cheap_alternative.id

    old_item = await db.get(QuoteItem, item_id)
    assert old_item.status == QuoteItemStatus.replaced

    new_item = await db.get(QuoteItem, result["new_item_id"])
    assert new_item.status == QuoteItemStatus.active


@pytest.mark.asyncio
async def test_add_same_product_increases_quantity(db: AsyncSession, quote: Quote, product_in_stock: Product):
    sess = str(uuid.uuid4())

    r1 = await add_to_quote(
        db,
        AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1),
        sess,
    )
    assert r1["action"] == "item_added"
    assert r1["new_quantity"] == 1

    r2 = await add_to_quote(
        db,
        AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2),
        sess,
    )
    assert r2["action"] == "quantity_increased"
    assert r2["new_quantity"] == 3

    rows = await db.execute(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.id,
            QuoteItem.product_id == product_in_stock.id,
            QuoteItem.status == QuoteItemStatus.active,
        )
    )
    assert len(rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_idempotency_key_prevents_duplicate_mutation(db: AsyncSession, quote: Quote, product_in_stock: Product):
    key = f"idem-{uuid.uuid4()}"
    sess = str(uuid.uuid4())

    r1 = await add_to_quote(
        db,
        AddToQuoteInput(
            quote_id=quote.id,
            product_id=product_in_stock.id,
            quantity=3,
            idempotency_key=key,
        ),
        sess,
    )
    assert r1.get("success") is True
    qty_after_first = r1["new_quantity"]

    r2 = await add_to_quote(
        db,
        AddToQuoteInput(
            quote_id=quote.id,
            product_id=product_in_stock.id,
            quantity=3,
            idempotency_key=key,
        ),
        sess,
    )
    assert r2.get("idempotent") is True

    item_result = await db.execute(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.id,
            QuoteItem.product_id == product_in_stock.id,
            QuoteItem.status == QuoteItemStatus.active,
        )
    )
    items = item_result.scalars().all()
    assert len(items) >= 1
    total_qty = sum(i.quantity for i in items)
    assert total_qty == qty_after_first


@pytest.mark.asyncio
async def test_price_limit_blocks_add(db: AsyncSession, quote: Quote, product_expensive: Product):
    result = await add_to_quote(
        db,
        AddToQuoteInput(
            quote_id=quote.id,
            product_id=product_expensive.id,
            quantity=1,
            max_price_try=5000.0,  # product costs 15000
        ),
        SESSION_ID,
    )
    assert "error" in result
    assert result.get("rule_violated") == "price_limit"

    rows = await db.execute(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.id,
            QuoteItem.product_id == product_expensive.id,
            QuoteItem.status == QuoteItemStatus.active,
        )
    )
    assert len(rows.scalars().all()) == 0


@pytest.mark.asyncio
async def test_out_of_stock_not_added_by_default(db: AsyncSession, quote: Quote, product_out_of_stock: Product):
    result = await add_to_quote(
        db,
        AddToQuoteInput(
            quote_id=quote.id,
            product_id=product_out_of_stock.id,
            quantity=1,
            allow_backorder=False,
        ),
        SESSION_ID,
    )
    assert "error" in result
    assert result.get("rule_violated") == "out_of_stock"


@pytest.mark.asyncio
async def test_out_of_stock_allowed_with_backorder(db: AsyncSession, quote: Quote, product_out_of_stock: Product):
    result = await add_to_quote(
        db,
        AddToQuoteInput(
            quote_id=quote.id,
            product_id=product_out_of_stock.id,
            quantity=1,
            allow_backorder=True,
        ),
        SESSION_ID,
    )
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_search_excludes_out_of_stock_by_default(db: AsyncSession, product_out_of_stock: Product):
    result = await search_products(
        db,
        SearchProductsInput(in_stock_only=True),
        SESSION_ID,
    )
    ids = [p["id"] for p in result["products"]]
    assert product_out_of_stock.id not in ids


@pytest.mark.asyncio
async def test_search_price_limit_filter(db: AsyncSession, product_expensive: Product, product_in_stock: Product):
    result = await search_products(
        db,
        SearchProductsInput(max_price_try=5000.0, in_stock_only=False),
        SESSION_ID,
    )
    for p in result["products"]:
        assert p["price_try"] <= 5000.0
    ids = [p["id"] for p in result["products"]]
    assert product_expensive.id not in ids


@pytest.mark.asyncio
async def test_fallback_retrieval_returns_knowledge_sources(
    db: AsyncSession,
    knowledge_return_policy: KnowledgeEntry,
):
    """SCN-009: Fallback must return sourced answer without LLM."""
    from app.schemas.schemas import ChatRequest
    from app.services.chat_service import stream_chat_fallback

    # FIX: stream_chat_fallback(request, db, session_id: str) imzası kullanıyor.
    # Eski testte ChatSession objesi geçiriliyordu — bu yanlıştı.
    sess_id = str(uuid.uuid4())

    request = ChatRequest(
        message="iade politikası nedir",
        session_id=sess_id,
    )

    events = []
    async for event in stream_chat_fallback(request, db, sess_id):
        events.append(event)

    # En az bir metin chunk gelmiş olmalı
    text_events = [e for e in events if "text_chunk" in e]
    assert len(text_events) > 0

    # get_knowledge_entries tool'u çağrılmış olmalı
    tool_events = [e for e in events if "tool_start" in e and "get_knowledge_entries" in e]
    assert len(tool_events) > 0

    # Stream done event'iyle bitmiş olmalı
    assert any("done" in e for e in events)


@pytest.mark.asyncio
async def test_fallback_does_not_call_llm(db: AsyncSession, monkeypatch):
    """LLM_ENABLED=False olduğunda LLM çağrısı yapılmamalı."""
    from app.core import config
    monkeypatch.setattr(config.settings, "OPENAI_API_KEY", None)
    assert config.settings.llm_enabled is False


@pytest.mark.asyncio
async def test_quote_state_consistent_across_reads(db: AsyncSession, quote: Quote, product_in_stock: Product):
    sess = str(uuid.uuid4())

    add_result = await add_to_quote(
        db,
        AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2),
        sess,
    )
    assert add_result.get("success") is True
    await db.commit()

    # Web ve mobil aynı veriyi görmeli
    web_result = await get_quote(db, GetQuoteInput(quote_id=quote.id), str(uuid.uuid4()))
    mobile_result = await get_quote(db, GetQuoteInput(quote_id=quote.id), str(uuid.uuid4()))

    assert web_result["quote_id"] == mobile_result["quote_id"]
    assert web_result["total_try"] == mobile_result["total_try"]
    assert web_result["active_items_count"] == mobile_result["active_items_count"]


@pytest.mark.asyncio
async def test_tool_calls_are_logged(db: AsyncSession, product_in_stock: Product):
    sess = str(uuid.uuid4())
    await search_products(
        db,
        SearchProductsInput(query="barkod"),
        sess,
    )
    await db.commit()

    logs = await db.execute(
        select(ToolCallLog).where(ToolCallLog.session_id == sess)
    )
    log_list = logs.scalars().all()
    assert len(log_list) >= 1
    assert log_list[0].tool_name == "search_products"
    assert log_list[0].status == "success"


@pytest.mark.asyncio
async def test_mutation_logs_quote_delta(db: AsyncSession, quote: Quote, product_in_stock: Product):
    sess = str(uuid.uuid4())
    await add_to_quote(
        db,
        AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1),
        sess,
    )
    await db.commit()

    logs = await db.execute(
        select(ToolCallLog).where(
            ToolCallLog.session_id == sess,
            ToolCallLog.tool_name == "add_to_quote",
        )
    )
    log = logs.scalar_one()
    assert log.quote_delta is not None
    assert "action" in log.quote_delta


@pytest.mark.asyncio
async def test_replace_marks_old_item_as_replaced(
    db: AsyncSession,
    quote: Quote,
    product_expensive: Product,
    product_cheap_alternative: Product,
):
    sess = str(uuid.uuid4())
    r = await add_to_quote(
        db,
        AddToQuoteInput(quote_id=quote.id, product_id=product_expensive.id, quantity=1),
        sess,
    )
    item_id = r["item_id"]

    await replace_with_alternative(
        db,
        ReplaceWithAlternativeInput(
            quote_id=quote.id,
            item_id=item_id,
            alternative_product_id=product_cheap_alternative.id,
        ),
        sess,
    )
    await db.commit()

    old_item = await db.get(QuoteItem, item_id)
    assert old_item.status == QuoteItemStatus.replaced
    assert old_item.replaced_by_item_id is not None

    active_rows = await db.execute(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.id,
            QuoteItem.status == QuoteItemStatus.active,
        )
    )
    active = active_rows.scalars().all()
    product_ids = [i.product_id for i in active]
    assert product_expensive.id not in product_ids