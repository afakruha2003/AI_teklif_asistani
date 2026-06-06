from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, computed_field


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    price_try: float
    stock: int = 0
    sku: Optional[str] = None
    aliases: List[str] = []
    tags: List[str] = []
    is_active: bool = True
    alternative_product_id: Optional[str] = None

class ProductCreate(ProductBase):
    id: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price_try: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None
    aliases: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    alternative_product_id: Optional[str] = None
    

class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime

class ProductSearchResult(ProductOut):
    relevance_score: Optional[float] = None


class KnowledgeEntryBase(BaseModel):
    title: str
    content: str
    category: str
    tags: List[str] = []
    is_active: bool = True

class KnowledgeEntryCreate(KnowledgeEntryBase):
    id: Optional[str] = None

class KnowledgeEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class KnowledgeEntryOut(KnowledgeEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str 
    company_name: Optional[str] = None 
    email: Optional[str] = None
    segment: str
    allow_backorder: bool
    price_level: str
    created_at: datetime


class QuoteItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    quote_id: str
    product_id: str
    quantity: int
    unit_price_try: float
    discount_pct: float
    status: str
    is_backorder: bool
    replaced_by_item_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductOut] = None

class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[QuoteItemOut] = []

    @computed_field
    @property
    def total_try(self) -> float:
        return sum(
            item.quantity * item.unit_price_try * (1 - item.discount_pct / 100)
            for item in self.items
            if item.status == "active"
        )


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    quote_id: Optional[str] = None
    customer_id: Optional[str] = None
    max_price_try: Optional[float] = None
    idempotency_key: Optional[str] = None

class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    quote_id: Optional[str] = None
    customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime


class ToolCallLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    tool_name: str
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    status: str
    quote_delta: Optional[Any] = None
    sequence_num: int
    duration_ms: Optional[int] = None
    idempotency_key: Optional[str] = None
    created_at: datetime


class SearchProductsInput(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    max_price_try: Optional[float] = None
    in_stock_only: bool = True
    tags: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)

class GetKnowledgeInput(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = Field(default=5, ge=1, le=20)

class GetQuoteInput(BaseModel):
    quote_id: str

class AddToQuoteInput(BaseModel):
    quote_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1)
    idempotency_key: Optional[str] = None
    max_price_try: Optional[float] = None
    allow_backorder: bool = False

class UpdateQuoteItemInput(BaseModel):
    quote_id: str
    item_id: str
    quantity: int = Field(ge=0)

class ReplaceWithAlternativeInput(BaseModel):
    quote_id: str
    item_id: str
    alternative_product_id: Optional[str] = None
    max_price_try: Optional[float] = None


class APIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None