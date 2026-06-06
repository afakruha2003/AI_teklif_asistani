from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.models.models import KnowledgeEntry
from app.schemas.schemas import KnowledgeEntryCreate, KnowledgeEntryOut, KnowledgeEntryUpdate, APIResponse

router = APIRouter()


@router.get("/", response_model=List[KnowledgeEntryOut])
async def list_knowledge(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)  # noqa: E712
    if category:
        stmt = stmt.where(func.lower(KnowledgeEntry.category) == category.lower())
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=KnowledgeEntryOut, status_code=201)
async def create_knowledge(body: KnowledgeEntryCreate, db: AsyncSession = Depends(get_db)):
    entry = KnowledgeEntry(id=body.id or str(uuid.uuid4()), **body.model_dump(exclude={"id"}))
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=KnowledgeEntryOut)
async def get_knowledge(entry_id: str, db: AsyncSession = Depends(get_db)):
    entry = await db.get(KnowledgeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.patch("/{entry_id}", response_model=KnowledgeEntryOut)
async def update_knowledge(
    entry_id: str, body: KnowledgeEntryUpdate, db: AsyncSession = Depends(get_db)
):
    entry = await db.get(KnowledgeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", response_model=APIResponse)
async def delete_knowledge(entry_id: str, db: AsyncSession = Depends(get_db)):
    entry = await db.get(KnowledgeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    entry.is_active = False
    await db.commit()
    return APIResponse(message="Knowledge entry deactivated")
