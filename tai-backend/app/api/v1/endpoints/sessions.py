from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import ChatSession, ChatMessage, ToolCallLog
from app.schemas.schemas import ChatSessionOut, ChatMessageOut, ToolCallLogOut

router = APIRouter()


@router.get("/", response_model=List[ChatSessionOut])
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ChatSession).offset(skip).limit(limit).order_by(ChatSession.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{session_id}", response_model=ChatSessionOut)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/messages", response_model=List[ChatMessageOut])
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{session_id}/tool-calls", response_model=List[ToolCallLogOut])
async def get_session_tool_calls(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ToolCallLog)
        .where(ToolCallLog.session_id == session_id)
        .order_by(ToolCallLog.sequence_num)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
