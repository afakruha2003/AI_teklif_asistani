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

# Modellerimizi artık güvenle import edebiliriz
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


# ─── Fixtures: Products ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def product_in_stock(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra DS2278 Kablosuz Barkod Okuyucu",
        description="Kablosuz 2D barkod okuyucu",
        category="barkod_okuyucu",
        price_try=2500.0,
        stock=10,
        aliases=["kablosuz okuyucu", "zebra okuyucu"],
        tags=["kablosuz", "barkod"],
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
        description="Endüstriyel el terminali",
        category="el_terminali",
        price_try=8500.0,
        stock=0,
        aliases=["el terminali", "honeywell ct45"],
        tags=["el_terminali"],
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_expensive(db: AsyncSession) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra ZT411 Endüstriyel Yazıcı",
        description="Yüksek hacimli endüstriyel etiket yazıcısı",
        category="yazici",
        price_try=15000.0,
        stock=5,
        aliases=["endüstriyel yazıcı"],
        tags=["yazıcı", "endüstriyel"],
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest_asyncio.fixture
async def product_cheap_alternative(db: AsyncSession, product_expensive: Product) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="Zebra ZD421 Masaüstü Yazıcı",
        description="Kompakt masaüstü etiket yazıcısı",
        category="yazici",
        price_try=4500.0,
        stock=8,
        aliases=["masaüstü yazıcı", "zd421"],
        tags=["yazıcı", "masaüstü"],
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    product_expensive.alternative_product_id = p.id
    await db.commit()
    return p


@pytest_asyncio.fixture
async def knowledge_return_policy(db: AsyncSession) -> KnowledgeEntry:
    k = KnowledgeEntry(
        id=str(uuid.uuid4()),
        title="İade Politikası",
        content="Ürünler teslimattan itibaren 14 gün içinde iade edilebilir. Yazılım lisansları iade edilemez.",
        category="return_policy",
        tags=["iade", "politika"],
    )
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k


@pytest_asyncio.fixture
async def customer_standard(db: AsyncSession) -> Customer:
    c = Customer(
        id=str(uuid.uuid4()),
        name="Test Müşteri",
        email="test@example.com",
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
        name="Partner Müşteri",
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
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return quote, item



    