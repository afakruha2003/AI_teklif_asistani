from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.models.models import Product
from app.schemas.schemas import ProductCreate, ProductOut, ProductUpdate, APIResponse

router = APIRouter()


@router.get("/", response_model=List[ProductOut])
async def list_products(
    category: Optional[str] = None,
    in_stock: Optional[bool] = None,
    max_price: Optional[float] = Query(None, alias="max_price_try"),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Product).where(Product.is_active == True)  # noqa: E712
    if category:
        stmt = stmt.where(func.lower(Product.category) == category.lower())
    if in_stock is True:
        stmt = stmt.where(Product.stock > 0)
    if max_price is not None:
        stmt = stmt.where(Product.price_try <= max_price)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = Product(id=body.id or str(uuid.uuid4()), **body.model_dump(exclude={"id"}))
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str, body: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=APIResponse)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    await db.commit()
    return APIResponse(message="Product deactivated")
