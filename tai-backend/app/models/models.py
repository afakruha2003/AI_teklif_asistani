from __future__ import annotations
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, Text, ForeignKey,
    JSON, Enum as SAEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Bizim core/database.py içindeki ortak çatımız
from app.core.database import Base

def _uuid() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc)

# ─── Enums ────────────────────────────────────────────────────────────────────

class QuoteStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"

class QuoteItemStatus(str, enum.Enum):
    active = "active"
    replaced = "replaced"
    removed = "removed"

class CustomerSegment(str, enum.Enum):
    standard = "standard"
    partner = "partner"
    enterprise = "enterprise"

class KnowledgeCategory(str, enum.Enum):
    return_policy = "return_policy"
    delivery = "delivery"
    warranty = "warranty"
    pricing = "pricing"
    stock = "stock"
    compatibility = "compatibility"
    fallback = "fallback"
    installation = "installation"
    general = "general"

class ToolCallStatus(str, enum.Enum):
    success = "success"
    error = "error"

# ─── Product ──────────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    price_try: Mapped[float] = mapped_column(Numeric(12, 2, asdecimal=False), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    
    aliases: Mapped[list] = mapped_column(JSONB, default=list)  # LLM'in eş anlamlı kelimeleri bulması için kritik!
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    alternative_product_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    alternative: Mapped[Optional["Product"]] = relationship(
        "Product", remote_side="Product.id", foreign_keys=[alternative_product_id]
    )
    quote_items: Mapped[List["QuoteItem"]] = relationship("QuoteItem", back_populates="product")
    price_rules: Mapped[List["PriceRule"]] = relationship("PriceRule", back_populates="product")

    __table_args__ = (
        Index("ix_products_category", "category"),
        Index("ix_products_is_active", "is_active"),
        Index("ix_products_price_try", "price_try"),
    )

# ─── Knowledge Entry ──────────────────────────────────────────────────────────

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        SAEnum(KnowledgeCategory, name="knowledge_category_enum"), nullable=False
    )
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (
        Index("ix_knowledge_category", "category"),
    )

# ─── Customer ─────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Yetkili Kişi Adı
    company_name: Mapped[Optional[str]] = mapped_column(String(255)) # EKLEDİK: Şirket Adı (Senaryolar için hayati)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    segment: Mapped[CustomerSegment] = mapped_column(
        SAEnum(CustomerSegment, name="customer_segment_enum"),
        default=CustomerSegment.standard,
    )
    allow_backorder: Mapped[bool] = mapped_column(Boolean, default=False) # Stok yoksa siparişe izin var mı?
    price_level: Mapped[str] = mapped_column(String(50), default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    quotes: Mapped[List["Quote"]] = relationship("Quote", back_populates="customer")

# ─── Price Rule ───────────────────────────────────────────────────────────────

class PriceRule(Base):
    __tablename__ = "price_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Kural Açıklaması (Örn: "Partner %10 İndirim")
    segment: Mapped[Optional[str]] = mapped_column(String(50))      # Hangi segmente özel?
    category: Mapped[Optional[str]] = mapped_column(String(100))    # Hangi kategoriye özel?
    product_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("products.id", ondelete="SET NULL"))
    
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)   # EKLEDİK: Miktar İndirimi Eşiği (Örn: 10 adet ve üzeri)
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)       # EKLEDİK: Çakışan kurallarda hangisi üstün?
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="price_rules")

# ─── Quote ────────────────────────────────────────────────────────────────────

class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[QuoteStatus] = mapped_column(
        SAEnum(QuoteStatus, name="quote_status_enum"), default=QuoteStatus.draft
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="quotes")
    items: Mapped[List["QuoteItem"]] = relationship(
        "QuoteItem", back_populates="quote", order_by="QuoteItem.created_at", cascade="all, delete-orphan"
    )

class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    quote_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_try: Mapped[float] = mapped_column(Numeric(12, 2, asdecimal=False), nullable=False) # Ham liste fiyatı
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), default=0)       # Uygulanan indirim oranı
    status: Mapped[QuoteItemStatus] = mapped_column(
        SAEnum(QuoteItemStatus, name="quote_item_status_enum"),
        default=QuoteItemStatus.active,
    )
    is_backorder: Mapped[bool] = mapped_column(Boolean, default=False) # Stok yetersiz ama siparişe onay verildi mi?
    replaced_by_item_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("quote_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    quote: Mapped["Quote"] = relationship("Quote", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="quote_items")

    __table_args__ = (
        Index("ix_quote_items_quote_id", "quote_id"),
        Index("ix_quote_items_product_id", "product_id"),
    )

# ─── Chat Session ─────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    quote_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", order_by="ChatMessage.created_at", cascade="all, delete-orphan"
    )
    tool_calls: Mapped[List["ToolCallLog"]] = relationship(
        "ToolCallLog", back_populates="session", order_by="ToolCallLog.sequence_num", cascade="all, delete-orphan"
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant / tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_id", "session_id"),
    )

# ─── Tool Call Log ────────────────────────────────────────────────────────────

class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Mükerrer istek koruması
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[ToolCallStatus] = mapped_column(
        SAEnum(ToolCallStatus, name="tool_call_status_enum"), default=ToolCallStatus.success
    )
    quote_delta: Mapped[Optional[dict]] = mapped_column(JSONB) # Sepette ne değişti? (Miktar artışı, silme logu vb.)
    sequence_num: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="tool_calls")

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_tool_call_idempotency_key"),
        Index("ix_tool_call_logs_session_id", "session_id"),
        Index("ix_tool_call_logs_tool_name", "tool_name"),
    )
    