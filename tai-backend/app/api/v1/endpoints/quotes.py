from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.models.models import Quote, QuoteItem, Customer
from app.schemas.schemas import QuoteOut, APIResponse

router = APIRouter()


@router.get("/", response_model=List[QuoteOut])
async def list_quotes(
    customer_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Quote)
        .options(selectinload(Quote.items).selectinload(QuoteItem.product))
        .offset(skip)
        .limit(limit)
        .order_by(Quote.created_at.desc())
    )
    if customer_id:
        stmt = stmt.where(Quote.customer_id == customer_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=QuoteOut, status_code=201)
async def create_quote(
    customer_id: Optional[str] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    quote = Quote(id=str(uuid.uuid4()), customer_id=customer_id, notes=notes)
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    quote.items = []
    return quote


@router.get("/{quote_id}", response_model=QuoteOut)
async def get_quote(quote_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.items).selectinload(QuoteItem.product))
    )
    result = await db.execute(stmt)
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
