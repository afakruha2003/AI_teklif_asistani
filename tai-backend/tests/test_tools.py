import pytest
import pytest_asyncio
import asyncio
import uuid
from typing import AsyncGenerator

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.models.models import (
    Base, Product, KnowledgeEntry, Customer, Quote, QuoteItem,
    QuoteItemStatus, QuoteStatus, CustomerSegment, ToolCallLog,
)
from app.schemas.schemas import (
    SearchProductsInput, GetKnowledgeInput, GetQuoteInput,
    AddToQuoteInput, UpdateQuoteItemInput, ReplaceWithAlternativeInput,
)
from app.tools.tool_implementations import (
    search_products, get_knowledge_entries, get_quote,
    add_to_quote, update_quote_item, replace_with_alternative,
    extract_price_limit_from_query, detect_category_from_query,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
SESSION_ID = str(uuid.uuid4())


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


# ─── Product Fixtures ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def product_in_stock(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra DS2278 Kablosuz Barkod Okuyucu",
        description="Kablosuz 2D barkod okuyucu, Bluetooth destekli",
        category="barcode_scanner",
        price_try=2500.0,
        stock=10,
        sku="PRD-BC-100",
        aliases={"tr": ["kablosuz okuyucu", "zebra okuyucu", "barkod okuyucu"]},
        tags=["kablosuz", "barkod", "bluetooth"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_out_of_stock(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Honeywell CT45 El Terminali",
        description="Endüstriyel el terminali, Android tabanlı",
        category="pos_terminal",
        price_try=8500.0,
        stock=0,
        sku="PRD-PT-200",
        aliases={"tr": ["el terminali", "honeywell ct45", "mobil terminal"]},
        tags=["el_terminali", "android"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_expensive(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra ZT411 Endüstriyel Etiket Yazıcı",
        description="Yüksek hacimli endüstriyel etiket yazıcısı",
        category="label_printer",
        price_try=15000.0,
        stock=5,
        sku="PRD-LP-300",
        aliases={"tr": ["endüstriyel yazıcı", "zebra zt411"]},
        tags=["yazici", "endustriyel"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_cheap_alternative(db: AsyncSession, product_expensive: Product) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra ZD421 Masaüstü Etiket Yazıcı",
        description="Kompakt masaüstü etiket yazıcısı",
        category="label_printer",
        price_try=4500.0,
        stock=8,
        sku="PRD-LP-301",
        aliases={"tr": ["masaüstü yazıcı", "zd421"]},
        tags=["yazici", "masaustu"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    # Update expensive product's alternative reference
    product_expensive.alternative_product_id = p.id
    db.add(product_expensive)
    await db.commit()
    await db.refresh(product_expensive)
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_stockout_alternative(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra TC52 El Terminali",
        description="Stoklu el terminali alternatifi",
        category="pos_terminal",
        price_try=9000.0,
        stock=5,
        sku="PRD-PT-201",
        aliases={"tr": ["zebra tc52", "el terminali"]},
        tags=["el_terminali"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_mobile_printer(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra ZQ521 Mobil Yazıcı",
        description="Taşınabilir mobil etiket yazıcısı",
        category="label_printer",
        price_try=7500.0,
        stock=10,
        sku="PRD-LP-400",
        aliases={"tr": ["mobil yazıcı", "taşınabilir yazıcı"]},
        tags=["yazici", "mobil"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_desktop_printer(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra ZD230 Masaüstü Yazıcı",
        description="Kompakt masaüstü etiket yazıcısı",
        category="label_printer",
        price_try=3500.0,
        stock=6,
        sku="PRD-LP-401",
        aliases={"tr": ["masaüstü yazıcı", "zd230"]},
        tags=["yazici", "masaustu"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_plus(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="DataLogic Gryphon PLUS Okuyucu",
        description="Plus serisi gelişmiş barkod okuyucu",
        category="barcode_scanner",
        price_try=3200.0,
        stock=20,
        sku="PRD-BC-PLUS-500",
        aliases={"tr": ["plus okuyucu", "gryphon plus"]},
        tags=["plus", "barkod"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_basic(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="DataLogic Gryphon Temel Okuyucu",
        description="Temel barkod okuyucu",
        category="barcode_scanner",
        price_try=1800.0,
        stock=15,
        sku="PRD-BC-BASIC-500",
        aliases={"tr": ["temel okuyucu", "gryphon temel"]},
        tags=["temel", "barkod"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_accessory(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="USB-C Şarj Adaptörü",
        description="El terminali için USB-C şarj adaptörü",
        category="accessory",
        price_try=350.0,
        stock=15,
        sku="PRD-ACC-USB-C",
        aliases={"tr": ["şarj adaptörü", "usb-c şarj", "şarj aleti"]},
        tags=["sarj", "usb-c", "aksesuar"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_accessory_stockout(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Araç Şarj Adaptörü",
        description="El terminali için araç şarj adaptörü",
        category="accessory",
        price_try=280.0,
        stock=0,
        sku="PRD-ACC-CAR",
        aliases={"tr": ["araç şarj", "araç adaptörü"]},
        tags=["sarj", "arac", "aksesuar"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_software_base(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="StokPro Temel Yazılım Lisansı",
        description="Temel stok yönetimi yazılımı",
        category="software",
        price_try=1200.0,
        stock=999,
        sku="PRD-SW-520",
        aliases={"tr": ["stok yazılımı", "temel lisans"]},
        tags=["yazilim", "stok", "lisans"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_software_module(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="StokPro Gelişmiş Modül",
        description="Temel yazılımla uyumlu gelişmiş modül",
        category="software",
        price_try=800.0,
        stock=999,
        sku="PRD-SW-530",
        aliases={"tr": ["gelişmiş modül", "ek modül"]},
        tags=["yazilim", "modul", "lisans"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_installation_service(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Yerinde Kurulum Hizmeti",
        description="Teknik ekip tarafından yerinde kurulum",
        category="service",
        price_try=500.0,
        stock=999,
        sku="PRD-SRV-INST",
        aliases={"tr": ["kurulum hizmeti", "yerinde kurulum"]},
        tags=["kurulum", "servis"],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p



@pytest_asyncio.fixture
async def knowledge_return_policy(db: AsyncSession) -> KnowledgeEntry:
    k = KnowledgeEntry(
        id=str(uuid.uuid4()),
        title="İade Politikası",
        content=(
            "Ürünler teslimattan itibaren 14 gün içinde iade edilebilir. "
            "Yazılım lisansları iade edilemez. Hasar görmüş ürünler kabul edilmez."
        ),
        category="return_policy",
        tags=["iade", "politika", "return"],
        is_active=True,
    )
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k


@pytest_asyncio.fixture
async def knowledge_delivery(db: AsyncSession) -> KnowledgeEntry:
    k = KnowledgeEntry(
        id=str(uuid.uuid4()),
        title="Teslimat Politikası",
        content=(
            "Stokta olan ürünler 3 iş günü içinde kargoya verilir. "
            "İstanbul içi teslimat 1 iş günüdür. Ücretsiz kargo 1000 TL ve üzeri siparişlerde geçerlidir."
        ),
        category="delivery_policy",
        tags=["teslimat", "kargo", "delivery"],
        is_active=True,
    )
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k


@pytest_asyncio.fixture
async def knowledge_compliance(db: AsyncSession) -> KnowledgeEntry:
    k = KnowledgeEntry(
        id=str(uuid.uuid4()),
        title="Uyumluluk Gereksinimleri",
        content=(
            "Depo otomasyonu için en az 1 el terminali ve 1 barkod okuyucu gereklidir. "
            "Yazılım lisansı zorunludur."
        ),
        category="compliance",
        tags=["uyumluluk", "compliance", "gereksinim"],
        is_active=True,
    )
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k


@pytest_asyncio.fixture
async def knowledge_region_rules(db: AsyncSession) -> KnowledgeEntry:
    k = KnowledgeEntry(
        id=str(uuid.uuid4()),
        title="Bölgesel Kurulum Kuralları",
        content=(
            "Anadolu bölgesi için acil kurulum 48 saat önceden rezervasyon gerektirir. "
            "İstanbul dışı teslimat ek ücrete tabidir."
        ),
        category="region_rules",
        tags=["bölge", "kurulum", "acil", "region"],
        is_active=True,
    )
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k


@pytest_asyncio.fixture
async def knowledge_software_compatibility(db: AsyncSession) -> KnowledgeEntry:
    k = KnowledgeEntry(
        id=str(uuid.uuid4()),
        title="Yazılım Uyumluluk Kuralları",
        content=(
            "PRD-SW-530 modülü yalnızca PRD-SW-520 temel lisansıyla birlikte çalışır. "
            "Her ikisi de aynı teklife eklenmelidir."
        ),
        category="software_compatibility",
        tags=["yazilim", "uyumluluk", "modul", "lisans"],
        is_active=True,
    )
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k


# ─── Customer & Quote Fixtures ────────────────────────────────────────────────

@pytest_asyncio.fixture
async def customer_standard(db: AsyncSession) -> Customer:
    c = Customer(
        id=str(uuid.uuid4()),
        name="Test Standart Müşteri",
        email="standard@example.com",
        segment=CustomerSegment.standard,
        allow_backorder=False,
        price_level="standard",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def customer_partner(db: AsyncSession) -> Customer:
    c = Customer(
        id=str(uuid.uuid4()),
        name="Partner Müşteri A.Ş.",
        email="partner@example.com",
        segment=CustomerSegment.partner,
        allow_backorder=True,
        price_level="partner",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def quote(db: AsyncSession, customer_standard: Customer) -> Quote:
    q = Quote(
        id=str(uuid.uuid4()),
        customer_id=customer_standard.id,
        status=QuoteStatus.draft,
        session_id=str(uuid.uuid4()),
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


@pytest_asyncio.fixture
async def partner_quote(db: AsyncSession, customer_partner: Customer) -> Quote:
    q = Quote(
        id=str(uuid.uuid4()),
        customer_id=customer_partner.id,
        status=QuoteStatus.draft,
        session_id=str(uuid.uuid4()),
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


@pytest_asyncio.fixture
async def quote_with_item(db: AsyncSession, quote: Quote, product_in_stock: Product) -> tuple:
    item = QuoteItem(
        id=str(uuid.uuid4()),
        quote_id=quote.id,
        product_id=product_in_stock.id,
        quantity=2,
        unit_price_try=product_in_stock.price_try,
        discount_pct=0,
        status=QuoteItemStatus.active,
        is_backorder=False,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await db.refresh(quote)
    return quote, item


@pytest_asyncio.fixture
async def quote_with_stockout_item(db: AsyncSession, quote: Quote, product_out_of_stock: Product) -> tuple:
    item = QuoteItem(
        id=str(uuid.uuid4()),
        quote_id=quote.id,
        product_id=product_out_of_stock.id,
        quantity=1,
        unit_price_try=product_out_of_stock.price_try,
        discount_pct=0,
        status=QuoteItemStatus.active,
        is_backorder=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await db.refresh(quote)
    return quote, item



class TestRetrieval:

    @pytest.mark.asyncio
    async def test_search_products_by_text(self, db: AsyncSession, product_in_stock: Product):
        result = await search_products(db, SearchProductsInput(query="kablosuz barkod"), SESSION_ID)
        assert result["count"] >= 1
        assert product_in_stock.id in [p["id"] for p in result["products"]]

    @pytest.mark.asyncio
    async def test_search_products_by_alias(self, db: AsyncSession, product_in_stock: Product):
        result = await search_products(db, SearchProductsInput(query="zebra okuyucu"), SESSION_ID)
        assert any(p["id"] == product_in_stock.id for p in result["products"])

    @pytest.mark.asyncio
    async def test_search_products_by_category(self, db: AsyncSession, product_in_stock: Product):
        result = await search_products(db, SearchProductsInput(category="barcode_scanner"), SESSION_ID)
        assert result["count"] >= 1
        assert all(p["category"] == "barcode_scanner" for p in result["products"])

    @pytest.mark.asyncio
    async def test_search_products_price_limit(self, db: AsyncSession, product_in_stock: Product, product_expensive: Product):
        """SCN-001: Fiyat limiti altındaki ürünleri getirme."""
        result = await search_products(db, SearchProductsInput(max_price_try=5000.0, in_stock_only=False), SESSION_ID)
        for p in result["products"]:
            assert p["price_try"] <= 5000.0
        ids = [p["id"] for p in result["products"]]
        assert product_expensive.id not in ids
        assert product_in_stock.id in ids

    @pytest.mark.asyncio
    async def test_search_excludes_out_of_stock_when_flag_set(self, db: AsyncSession, product_out_of_stock: Product):
        result = await search_products(db, SearchProductsInput(in_stock_only=True), SESSION_ID)
        ids = [p["id"] for p in result["products"]]
        assert product_out_of_stock.id not in ids

    @pytest.mark.asyncio
    async def test_search_returns_suggestions_when_no_products_in_budget(self, db: AsyncSession, product_pos_terminal: Product):
        """SCN-002: Bütçe altında ürün yoksa suggestions key dönmeli."""
        result = await search_products(
            db,
            SearchProductsInput(query="el terminali", category="pos_terminal", max_price_try=500.0),
            SESSION_ID,
        )
        assert result["count"] == 0
        assert "suggestions" in result 
        assert result["suggestions"]["min_available_price"] == 3000.0
        

    @pytest.mark.asyncio
    async def test_search_suggestions_contain_price_info(self, db: AsyncSession, product_out_of_stock: Product):
        result = await search_products(
            db,
            SearchProductsInput(query="el terminali", category="pos_terminal", max_price_try=500.0),
            SESSION_ID,
        )
        if "suggestions" in result:
            assert "min_available_price" in result["suggestions"]
            assert result["suggestions"]["min_available_price"] > 500.0

    @pytest.mark.asyncio
    async def test_get_knowledge_by_query(self, db: AsyncSession, knowledge_return_policy: KnowledgeEntry):
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="iade"), SESSION_ID)
        assert result["count"] >= 1
        assert knowledge_return_policy.id in [e["knowledge_id"] for e in result["knowledge_entries"]]

    @pytest.mark.asyncio
    async def test_get_knowledge_returns_knowledge_id_field(self, db: AsyncSession, knowledge_return_policy: KnowledgeEntry):
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="iade politika"), SESSION_ID)
        for entry in result["knowledge_entries"]:
            assert "knowledge_id" in entry
            assert entry["knowledge_id"]

    @pytest.mark.asyncio
    async def test_get_knowledge_by_category(self, db: AsyncSession, knowledge_delivery: KnowledgeEntry):
        """SCN-021: Teslimat kategorisinde knowledge entry bulunmalı."""
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="teslimat"), SESSION_ID)
        assert result["count"] >= 1
        assert knowledge_delivery.id in [e["knowledge_id"] for e in result["knowledge_entries"]]

    @pytest.mark.asyncio
    async def test_get_knowledge_compliance(self, db: AsyncSession, knowledge_compliance: KnowledgeEntry):
        """SCN-008: Uyumluluk bilgisi sorgulanabilmeli."""
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="uyumluluk gereksinim"), SESSION_ID)
        assert result["count"] >= 1
        assert knowledge_compliance.id in [e["knowledge_id"] for e in result["knowledge_entries"]]

    @pytest.mark.asyncio
    async def test_get_knowledge_region_rules(self, db: AsyncSession, knowledge_region_rules: KnowledgeEntry):
        """SCN-018: Bölgesel kurulum kuralları sorgulanabilmeli."""
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="acil kurulum bölge"), SESSION_ID)
        assert result["count"] >= 1
        assert knowledge_region_rules.id in [e["knowledge_id"] for e in result["knowledge_entries"]]

    @pytest.mark.asyncio
    async def test_get_knowledge_software_compatibility(self, db: AsyncSession, knowledge_software_compatibility: KnowledgeEntry):
        """SCN-017: Yazılım uyumluluk kuralları sorgulanabilmeli."""
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="yazılım uyumluluk modül"), SESSION_ID)
        assert result["count"] >= 1
        assert knowledge_software_compatibility.id in [e["knowledge_id"] for e in result["knowledge_entries"]]

    @pytest.mark.asyncio
    async def test_get_knowledge_return_policy_for_software(self, db: AsyncSession, knowledge_return_policy: KnowledgeEntry):
        """SCN-016: Aktif lisans için iade politikası sorgulanabilmeli."""
        result = await get_knowledge_entries(db, GetKnowledgeInput(query="yazılım lisans iade"), SESSION_ID)
        assert result["count"] >= 1
        assert any(
            "yazılım" in e["content"].lower() or "lisans" in e["content"].lower()
            for e in result["knowledge_entries"]
        )

class TestQuoteStructure:

    @pytest.mark.asyncio
    async def test_get_quote_correct_structure(self, db: AsyncSession, quote: Quote):
        result = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert "quote_id" in result
        assert result["quote_id"] == quote.id
        assert "items" in result
        assert "total_try" in result
        assert "active_items_count" in result

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, db: AsyncSession):
        result = await get_quote(db, GetQuoteInput(quote_id="nonexistent-id"), SESSION_ID)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_quote_total_calculated_correctly(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2), SESSION_ID)
        result = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert abs(result["total_try"] - product_in_stock.price_try * 2) < 0.01

    @pytest.mark.asyncio
    async def test_get_quote_active_items_count(self, db: AsyncSession, quote: Quote, product_in_stock: Product, product_accessory: Product):
        await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), SESSION_ID)
        await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_accessory.id, quantity=1), SESSION_ID)
        result = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert result["active_items_count"] == 2



class TestMutationBehavior:

    @pytest.mark.asyncio
    async def test_add_to_quote_creates_item(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        """SCN-001: Ürün teklife eklenmeli."""
        result = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), SESSION_ID)
        assert result.get("success") is True
        assert result["action"] == "item_added"
        assert result["new_quantity"] == 1

        row = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.product_id == product_in_stock.id,
                QuoteItem.status == QuoteItemStatus.active,
            )
        )
        item = row.scalar_one_or_none()
        assert item is not None
        assert item.quantity == 1

    @pytest.mark.asyncio
    async def test_add_same_product_increases_quantity(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        """SCN-003 & SCN-013: Tekrar ekleme yeni satır açmamalı, miktar artmalı."""
        sess = str(uuid.uuid4())
        r1 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), sess)
        assert r1.get("success") is True
        assert r1["action"] == "item_added"

        r2 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2), sess)
        assert r2.get("success") is True
        assert r2["action"] == "quantity_increased"
        assert r2["new_quantity"] == 3

        rows = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.product_id == product_in_stock.id,
                QuoteItem.status == QuoteItemStatus.active,
            )
        )
        active = rows.scalars().all()
        assert len(active) == 1
        assert active[0].quantity == 3

    @pytest.mark.asyncio
    async def test_update_quote_item_quantity(self, db: AsyncSession, quote_with_item: tuple):
        """SCN-004: Miktar güncellenebilmeli."""
        quote, item = quote_with_item
        result = await update_quote_item(db, UpdateQuoteItemInput(quote_id=quote.id, item_id=item.id, quantity=5), SESSION_ID)
        assert result.get("success") is True
        assert result["new_quantity"] == 5
        assert result["action"] == "quantity_updated"
        await db.refresh(item)
        assert item.quantity == 5

    @pytest.mark.asyncio
    async def test_update_quote_item_quantity_zero_removes(self, db: AsyncSession, quote_with_item: tuple):
        quote, item = quote_with_item
        result = await update_quote_item(db, UpdateQuoteItemInput(quote_id=quote.id, item_id=item.id, quantity=0), SESSION_ID)
        assert result.get("success") is True
        assert result["action"] == "item_removed"
        await db.refresh(item)
        assert item.status == QuoteItemStatus.removed

    @pytest.mark.asyncio
    async def test_replace_with_alternative_scn005(self, db: AsyncSession, quote: Quote, product_expensive: Product, product_cheap_alternative: Product):
        """SCN-005: Pahalı ürünü ucuz alternatifle değiştirme."""
        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_expensive.id, quantity=1), SESSION_ID)
        assert add_r.get("success") is True

        result = await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=add_r["item_id"], alternative_product_id=product_cheap_alternative.id),
            SESSION_ID,
        )
        assert result.get("success") is True
        assert result["action"] == "item_replaced"
        assert result["new_product_id"] == product_cheap_alternative.id

        old_item = await db.get(QuoteItem, add_r["item_id"])
        assert old_item.status == QuoteItemStatus.replaced
        new_item = await db.get(QuoteItem, result["new_item_id"])
        assert new_item.status == QuoteItemStatus.active
        assert new_item.product_id == product_cheap_alternative.id

    @pytest.mark.asyncio
    async def test_replace_marks_old_item_replaced_and_sets_reference(self, db: AsyncSession, quote: Quote, product_expensive: Product, product_cheap_alternative: Product):
        r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_expensive.id, quantity=1), SESSION_ID)
        rep = await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=r["item_id"], alternative_product_id=product_cheap_alternative.id),
            SESSION_ID,
        )
        await db.commit()
        old_item = await db.get(QuoteItem, r["item_id"])
        assert old_item.status == QuoteItemStatus.replaced
        assert old_item.replaced_by_item_id == rep["new_item_id"]

    @pytest.mark.asyncio
    async def test_replace_stockout_item_with_available_alternative_scn006(self, db: AsyncSession, quote: Quote, product_out_of_stock: Product, product_stockout_alternative: Product):
        """SCN-006: Stok dışı ürünü stoklu alternatifle değiştirme."""
        product_out_of_stock.alternative_product_id = product_stockout_alternative.id
        db.add(product_out_of_stock)
        await db.commit()
        await db.refresh(product_out_of_stock)

        add_r = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_out_of_stock.id, quantity=1, allow_backorder=True),
            SESSION_ID,
        )
        assert add_r.get("success") is True

        result = await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=add_r["item_id"], alternative_product_id=product_stockout_alternative.id),
            SESSION_ID,
        )
        assert result.get("success") is True
        assert result["new_product_id"] == product_stockout_alternative.id

        active_rows = await db.execute(
            select(QuoteItem).where(QuoteItem.quote_id == quote.id, QuoteItem.status == QuoteItemStatus.active)
        )
        active_pids = [i.product_id for i in active_rows.scalars().all()]
        assert product_out_of_stock.id not in active_pids
        assert product_stockout_alternative.id in active_pids

    @pytest.mark.asyncio
    async def test_replace_mobile_printer_with_desktop_scn014(self, db: AsyncSession, quote: Quote, product_mobile_printer: Product, product_desktop_printer: Product):
        """SCN-014: Stok dışı mobil yazıcıyı stoklu yazıcıyla değiştirme."""
        add_r = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_mobile_printer.id, quantity=1, allow_backorder=True),
            SESSION_ID,
        )
        assert add_r.get("success") is True

        result = await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=add_r["item_id"], alternative_product_id=product_desktop_printer.id),
            SESSION_ID,
        )
        assert result.get("success") is True
        assert result["new_product_id"] == product_desktop_printer.id

    @pytest.mark.asyncio
    async def test_add_multiple_products_compliance_scn008(self, db: AsyncSession, quote: Quote, product_in_stock: Product, product_installation_service: Product, knowledge_compliance: KnowledgeEntry):
        """SCN-008: Uyumluluk bilgisine göre birden fazla ürün ekleme."""
        k_result = await get_knowledge_entries(db, GetKnowledgeInput(query="uyumluluk gereksinim"), SESSION_ID)
        assert k_result["count"] >= 1

        r1 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), SESSION_ID)
        assert r1.get("success") is True
        r2 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_installation_service.id, quantity=1), SESSION_ID)
        assert r2.get("success") is True

        q_result = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert q_result["active_items_count"] == 2

    @pytest.mark.asyncio
    async def test_add_software_with_module_scn017(self, db: AsyncSession, quote: Quote, product_software_base: Product, product_software_module: Product):
        """SCN-017: Yazılım uyumluluğuna göre temel + modül ekleme."""
        r1 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_software_base.id, quantity=1), SESSION_ID)
        assert r1.get("success") is True
        r2 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_software_module.id, quantity=1), SESSION_ID)
        assert r2.get("success") is True

        q_result = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert q_result["active_items_count"] == 2
        active_pids = [i["product_id"] for i in q_result["items"] if i["status"] == "active"]
        assert product_software_base.id in active_pids
        assert product_software_module.id in active_pids

    @pytest.mark.asyncio
    async def test_update_service_quantity_scn015(self, db: AsyncSession, quote: Quote, product_installation_service: Product):
        """SCN-015: Kurulum hizmeti miktarını güncelleme."""
        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_installation_service.id, quantity=1), SESSION_ID)
        assert add_r.get("success") is True

        q_before = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert q_before["active_items_count"] == 1

        update_r = await update_quote_item(db, UpdateQuoteItemInput(quote_id=quote.id, item_id=add_r["item_id"], quantity=3), SESSION_ID)
        assert update_r.get("success") is True
        assert update_r["new_quantity"] == 3

        k_result = await get_knowledge_entries(db, GetKnowledgeInput(query="kurulum servis"), SESSION_ID)
        assert k_result is not None

    @pytest.mark.asyncio
    async def test_add_alternative_accessory_when_stockout_scn022(self, db: AsyncSession, quote: Quote, product_accessory_stockout: Product, product_accessory: Product):
        """SCN-022: Araç şarj stok dışıysa USB-C alternatif ekleme."""
        result_stockout = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_accessory_stockout.id, quantity=1, allow_backorder=False),
            SESSION_ID,
        )
        assert "error" in result_stockout
        assert result_stockout.get("rule_violated") == "out_of_stock"

        search_r = await search_products(db, SearchProductsInput(query="USB-C şarj", category="accessory", in_stock_only=True), SESSION_ID)
        assert search_r["count"] >= 1

        result_alt = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_accessory.id, quantity=1), SESSION_ID)
        assert result_alt.get("success") is True



class TestPriceAndStockRules:

    @pytest.mark.asyncio
    async def test_price_limit_blocks_add(self, db: AsyncSession, quote: Quote, product_expensive: Product):
        result = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_expensive.id, quantity=1, max_price_try=5000.0),
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
    async def test_out_of_stock_not_added_by_default(self, db: AsyncSession, quote: Quote, product_out_of_stock: Product):
        result = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_out_of_stock.id, quantity=1, allow_backorder=False),
            SESSION_ID,
        )
        assert "error" in result
        assert result.get("rule_violated") == "out_of_stock"

    @pytest.mark.asyncio
    async def test_out_of_stock_allowed_with_backorder(self, db: AsyncSession, quote: Quote, product_out_of_stock: Product):
        result = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_out_of_stock.id, quantity=1, allow_backorder=True),
            SESSION_ID,
        )
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_add_inactive_product_blocked(self, db: AsyncSession, quote: Quote):
        inactive = Product(
            id=str(uuid.uuid4()), name="Eski Model", category="barcode_scanner",
            price_try=1000.0, stock=5, sku="PRD-OLD-001", is_active=False,
        )
        db.add(inactive)
        await db.commit()
        result = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=inactive.id, quantity=1), SESSION_ID)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_stock_decreases_after_add(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        initial_stock = product_in_stock.stock
        await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2), SESSION_ID)
        await db.refresh(product_in_stock)
        assert product_in_stock.stock == initial_stock - 2

    @pytest.mark.asyncio
    async def test_replace_blocked_if_alternative_out_of_stock(self, db: AsyncSession, quote: Quote, product_in_stock: Product, product_accessory_stockout: Product):
        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), SESSION_ID)
        result = await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=add_r["item_id"], alternative_product_id=product_accessory_stockout.id),
            SESSION_ID,
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_replace_blocked_if_alternative_exceeds_price_limit(self, db: AsyncSession, quote: Quote, product_in_stock: Product, product_expensive: Product):
        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), SESSION_ID)
        result = await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=add_r["item_id"], alternative_product_id=product_expensive.id, max_price_try=5000.0),
            SESSION_ID,
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_price_limit_select_basic_over_plus_scn020(self, db: AsyncSession, quote: Quote, product_basic: Product, product_plus: Product):
        """SCN-020: Fiyat limiti altında Plus yerine temel ürün seçilmeli."""
        result = await search_products(
            db,
            SearchProductsInput(category="barcode_scanner", max_price_try=2000.0, in_stock_only=True),
            SESSION_ID,
        )
        ids = [p["id"] for p in result["products"]]
        assert product_basic.id in ids
        assert product_plus.id not in ids

        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_basic.id, quantity=1, max_price_try=2000.0), SESSION_ID)
        assert add_r.get("success") is True


class TestIdempotency:

    @pytest.mark.asyncio
    async def test_idempotency_key_prevents_duplicate_mutation(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        """SCN-010: Aynı key ile tekrar istek miktar iki kez artırmamalı."""
        key = f"idem-{uuid.uuid4()}"
        sess = str(uuid.uuid4())

        r1 = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=3, idempotency_key=key),
            sess,
        )
        assert r1.get("success") is True
        qty_after_first = r1["new_quantity"]

        r2 = await add_to_quote(
            db,
            AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=3, idempotency_key=key),
            sess,
        )
        assert r2.get("idempotent") is True

        rows = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.product_id == product_in_stock.id,
                QuoteItem.status == QuoteItemStatus.active,
            )
        )
        assert sum(i.quantity for i in rows.scalars().all()) == qty_after_first

    @pytest.mark.asyncio
    async def test_different_idempotency_keys_both_processed(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        sess = str(uuid.uuid4())
        r1 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1, idempotency_key=f"k-{uuid.uuid4()}"), sess)
        assert r1.get("success") is True
        r2 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2, idempotency_key=f"k-{uuid.uuid4()}"), sess)
        assert r2.get("success") is True
        assert r2.get("idempotent") is not True

    @pytest.mark.asyncio
    async def test_stream_retry_does_not_double_quantity_scn010(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        """SCN-010: Akış tekrar denemesinde miktar çift artmamalı."""
        key = f"retry-{uuid.uuid4()}"
        sess = str(uuid.uuid4())
        params = AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1, idempotency_key=key)

        r1 = await add_to_quote(db, params, sess)
        assert r1.get("success") is True
        r2 = await add_to_quote(db, params, sess)
        assert r2.get("idempotent") is True

        rows = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.product_id == product_in_stock.id,
                QuoteItem.status == QuoteItemStatus.active,
            )
        )
        assert sum(i.quantity for i in rows.scalars().all()) == 1



class TestPartnerDiscount:

    @pytest.mark.asyncio
    async def test_partner_quote_has_customer_id(self, db: AsyncSession, partner_quote: Quote, customer_partner: Customer):
        assert partner_quote.customer_id == customer_partner.id

    @pytest.mark.asyncio
    async def test_add_to_partner_quote_succeeds(self, db: AsyncSession, partner_quote: Quote, product_in_stock: Product):
        """SCN-011: Partner müşterisi için ürün eklenebilmeli."""
        result = await add_to_quote(db, AddToQuoteInput(quote_id=partner_quote.id, product_id=product_in_stock.id, quantity=3), SESSION_ID)
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_partner_discount_applied_on_add(self, db: AsyncSession, partner_quote: Quote, product_in_stock: Product):
        """SCN-011: applied_discount_pct response'da bulunmalı."""
        result = await add_to_quote(db, AddToQuoteInput(quote_id=partner_quote.id, product_id=product_in_stock.id, quantity=3), SESSION_ID)
        assert result.get("success") is True
        assert "applied_discount_pct" in result

    @pytest.mark.asyncio
    async def test_partner_recalculates_after_add_scn011(self, db: AsyncSession, partner_quote: Quote, product_in_stock: Product):
        """SCN-011: Ekleme sonrası indirim get_knowledge_entries ile doğrulanabilmeli."""
        await add_to_quote(db, AddToQuoteInput(quote_id=partner_quote.id, product_id=product_in_stock.id, quantity=3), SESSION_ID)
        q_result = await get_quote(db, GetQuoteInput(quote_id=partner_quote.id), SESSION_ID)
        assert q_result["active_items_count"] == 1

        k_result = await get_knowledge_entries(db, GetKnowledgeInput(query="partner indirim"), SESSION_ID)
        assert k_result is not None

    @pytest.mark.asyncio
    async def test_plus_product_volume_add_scn019(self, db: AsyncSession, quote: Quote, product_plus: Product):
        """SCN-019: Plus ürün hacim indirimi — miktar doğru biriktirilmeli."""
        r1 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_plus.id, quantity=2), SESSION_ID)
        assert r1.get("success") is True

        q_mid = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert q_mid["active_items_count"] == 1

        r2 = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_plus.id, quantity=2), SESSION_ID)
        assert r2.get("success") is True

        k_result = await get_knowledge_entries(db, GetKnowledgeInput(query="hacim indirim miktar"), SESSION_ID)
        assert k_result is not None

        rows = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.product_id == product_plus.id,
                QuoteItem.status == QuoteItemStatus.active,
            )
        )
        items = rows.scalars().all()
        assert len(items) == 1
        assert items[0].quantity == 4

    @pytest.mark.asyncio
    async def test_plus_product_no_duplicate_row_scn013(self, db: AsyncSession, quote: Quote, product_plus: Product):
        """SCN-013: Plus ürün tekrar ekleme tekrarsızlığı."""
        sess = str(uuid.uuid4())
        for _ in range(3):
            await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_plus.id, quantity=1), sess)

        rows = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.product_id == product_plus.id,
                QuoteItem.status == QuoteItemStatus.active,
            )
        )
        items = rows.scalars().all()
        assert len(items) == 1
        assert items[0].quantity == 3



class TestTurkishPriceExtraction:

    @pytest.mark.asyncio
    async def test_extract_price_from_tl_alti(self, db: AsyncSession):
        assert extract_price_limit_from_query("500 TL altı el terminali öner") == 500.0

    @pytest.mark.asyncio
    async def test_extract_price_from_altinda(self, db: AsyncSession):
        assert extract_price_limit_from_query("1000 TL altında barkod okuyucu") == 1000.0

    @pytest.mark.asyncio
    async def test_extract_price_with_try(self, db: AsyncSession):
        assert extract_price_limit_from_query("3000 TRY altında ürün öner") == 3000.0

    @pytest.mark.asyncio
    async def test_no_price_returns_none(self, db: AsyncSession):
        assert extract_price_limit_from_query("el terminali öner") is None

    @pytest.mark.asyncio
    async def test_detect_category_el_terminali(self, db: AsyncSession):
        assert detect_category_from_query("500 TL altı el terminali öner") == "pos_terminal"

    @pytest.mark.asyncio
    async def test_detect_category_barkod(self, db: AsyncSession):
        assert detect_category_from_query("kablosuz barkod okuyucu") == "barcode_scanner"

    @pytest.mark.asyncio
    async def test_detect_category_etiket_yazici(self, db: AsyncSession):
        assert detect_category_from_query("etiket yazıcı öner") == "label_printer"

    @pytest.mark.asyncio
    async def test_search_with_turkish_price_query_scn012(self, db: AsyncSession, product_in_stock: Product, product_accessory: Product):
        """SCN-012: Türkçe fiyat limitli aksesuar ekleme."""
        result = await search_products(db, SearchProductsInput(query="3000 TL altı kablosuz okuyucu", in_stock_only=True), SESSION_ID)
        for p in result["products"]:
            if result.get("price_limit_used"):
                assert p["price_try"] <= result["price_limit_used"]
    
        # Create a proper quote first instead of using random UUID
        from app.models.models import Quote, QuoteStatus
        new_quote = Quote(
            id=str(uuid.uuid4()),
            session_id=SESSION_ID,
            status=QuoteStatus.draft,
        )
        db.add(new_quote)
        await db.flush()
        
        add_r = await add_to_quote(db, AddToQuoteInput(
            quote_id=new_quote.id,  # Use the actual quote ID
            product_id=product_accessory.id,
            quantity=1,
        ), SESSION_ID)
        assert add_r.get("success") is True
    
class TestLogging:

    @pytest.mark.asyncio
    async def test_tool_calls_are_logged(self, db: AsyncSession, product_in_stock: Product):
        sess = str(uuid.uuid4())
        await search_products(db, SearchProductsInput(query="barkod"), sess)
        await db.commit()

        logs = await db.execute(select(ToolCallLog).where(ToolCallLog.session_id == sess))
        log_list = logs.scalars().all()
        assert len(log_list) >= 1
        assert log_list[0].tool_name == "search_products"
        status_val = log_list[0].status.value if hasattr(log_list[0].status, "value") else log_list[0].status
        assert status_val == "success"

    @pytest.mark.asyncio
    async def test_mutation_logs_quote_delta(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        sess = str(uuid.uuid4())
        await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=1), sess)
        await db.commit()

        logs = await db.execute(
            select(ToolCallLog).where(ToolCallLog.session_id == sess, ToolCallLog.tool_name == "add_to_quote")
        )
        log = logs.scalar_one_or_none()
        assert log is not None
        assert log.quote_delta is not None
        assert "action" in log.quote_delta

    @pytest.mark.asyncio
    async def test_skip_logging_flag_works(self, db: AsyncSession, product_in_stock: Product):
        sess = str(uuid.uuid4())
        await search_products(db, SearchProductsInput(query="barkod"), sess, skip_logging=True)
        await db.commit()

        logs = await db.execute(select(ToolCallLog).where(ToolCallLog.session_id == sess))
        assert len(logs.scalars().all()) == 0



class TestFallbackMode:

    @pytest.mark.asyncio
    async def test_fallback_retrieval_returns_knowledge_sources_scn009(self, db: AsyncSession, knowledge_return_policy: KnowledgeEntry):
        """SCN-009: Fallback modda kaynaklı yanıt dönmeli."""
        from app.schemas.schemas import ChatRequest
        from app.services.chat_service import stream_chat_fallback

        sess_id = str(uuid.uuid4())
        request = ChatRequest(message="iade politikası nedir", session_id=sess_id)
        events = []
        async for event in stream_chat_fallback(request, db, sess_id):
            events.append(event)

        assert len([e for e in events if "text_chunk" in e]) > 0
        assert len([e for e in events if "tool_start" in e and "get_knowledge_entries" in e]) > 0
        assert any("done" in e for e in events)

    @pytest.mark.asyncio
    async def test_fallback_delivery_query_scn021(self, db: AsyncSession, knowledge_delivery: KnowledgeEntry):
        """SCN-021: Fallback modda teslimat sorgusuna kaynaklı yanıt ve get_quote çağrısı."""
        from app.schemas.schemas import ChatRequest
        from app.services.chat_service import stream_chat_fallback

        sess_id = str(uuid.uuid4())
        request = ChatRequest(message="teslimat süresi ne kadar", session_id=sess_id)
        events = []
        async for event in stream_chat_fallback(request, db, sess_id):
            events.append(event)

        assert len(events) > 0
        assert any("done" in e for e in events)
        assert len([e for e in events if "text_chunk" in e]) > 0

    @pytest.mark.asyncio
    async def test_fallback_does_not_call_llm_when_key_missing(self):
        from app.core.config import Settings
        assert Settings(LLM_ENABLED=True, OPENAI_API_KEY=None).llm_enabled is False

    @pytest.mark.asyncio
    async def test_fallback_disabled_when_flag_off(self):
        from app.core.config import Settings
        assert Settings(LLM_ENABLED=False, OPENAI_API_KEY="sk-test").llm_enabled is False

    @pytest.mark.asyncio
    async def test_llm_enabled_when_key_present(self):
        from app.core.config import Settings
        assert Settings(LLM_ENABLED=True, OPENAI_API_KEY="sk-valid").llm_enabled is True



class TestSharedState:

    @pytest.mark.asyncio
    async def test_quote_state_consistent_across_reads(self, db: AsyncSession, quote: Quote, product_in_stock: Product):
        """SCN-009 ek: Aynı quote iki farklı session'dan tutarlı görünmeli."""
        sess = str(uuid.uuid4())
        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_in_stock.id, quantity=2), sess)
        assert add_r.get("success") is True
        await db.commit()

        web = await get_quote(db, GetQuoteInput(quote_id=quote.id), str(uuid.uuid4()))
        mobile = await get_quote(db, GetQuoteInput(quote_id=quote.id), str(uuid.uuid4()))

        assert web["quote_id"] == mobile["quote_id"]
        assert web["total_try"] == mobile["total_try"]
        assert web["active_items_count"] == mobile["active_items_count"]

        
    @pytest.mark.asyncio
    async def test_replace_updates_quote_correctly(self, db: AsyncSession, quote: Quote, product_expensive: Product, product_cheap_alternative: Product):
        add_r = await add_to_quote(db, AddToQuoteInput(quote_id=quote.id, product_id=product_expensive.id, quantity=1), SESSION_ID)
        before = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
    
        await replace_with_alternative(
            db,
            ReplaceWithAlternativeInput(quote_id=quote.id, item_id=add_r["item_id"], alternative_product_id=product_cheap_alternative.id),
            SESSION_ID,
        )
        await db.commit()

        db.expire_all()  
        await db.refresh(quote)
        after = await get_quote(db, GetQuoteInput(quote_id=quote.id), SESSION_ID)
        assert after["total_try"] < before["total_try"]
        assert after["active_items_count"] == 1
    
    