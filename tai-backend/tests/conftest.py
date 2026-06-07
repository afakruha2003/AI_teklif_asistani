"""
Test configuration with SQLite in-memory database.
No real PostgreSQL required for tests.
"""
import pytest
import pytest_asyncio
import asyncio
import uuid
from typing import AsyncGenerator

# 🚀 SİHİRLİ DOKUNUŞ (MONKEY-PATCH): 
# Modeller import edilmeden HEMEN ÖNCE SQLite'a JSONB tipini öğretiyoruz.
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
# ---------------------------------------------------------

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.models.models import (
    Base, Product, KnowledgeEntry, Customer, Quote, QuoteItem,
    QuoteItemStatus, QuoteStatus, CustomerSegment,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create database engine with NullPool to avoid connection issues."""
    eng = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database(engine):
    """Create and drop database tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh session for each test with proper transaction management."""
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        try:
            async with session.begin():
                yield session
        finally:
            await session.rollback()
            await session.expunge_all()
            await session.close()


# ═══════════════════════════════════════════════════════════════════════════════════
# PRODUCT FIXTURES - All categories properly standardized
# ═══════════════════════════════════════════════════════════════════════════════════

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
    """Product with stock=0 - should be filtered out when in_stock_only=True."""
    p = Product(
        id=str(uuid.uuid4()),
        name="Honeywell CT45 El Terminali",
        description="Endüstriyel el terminali, Android tabanlı",
        category="pos_terminal",
        price_try=8500.0,
        stock=0,  # CRITICAL: stock must be 0 for out-of-stock tests
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
async def product_pos_terminal(db: AsyncSession) -> Product:
    """In-stock POS terminal for suggestions testing."""
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra TC21 Basic El Terminali",
        description="Giriş seviye el terminali",
        category="pos_terminal",
        price_try=3000.0,
        stock=10,
        sku="PRD-PT-300",
        aliases={"tr": ["zebra tc21", "el terminali"]},
        tags=["el_terminali"],
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
        stock=0,  # Out of stock for replacement test
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


# ═══════════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════════
# CUSTOMER & QUOTE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════════

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

    