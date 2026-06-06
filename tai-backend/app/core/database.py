from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


SYNC_URL = settings.DATABASE_URL
ASYNC_URL = SYNC_URL.replace("postgresql://", "postgresql+asyncpg://") if "postgresql+asyncpg://" not in SYNC_URL else SYNC_URL


engine = create_async_engine(
    ASYNC_URL,
    pool_pre_ping=True, 
    pool_size=10,         
    max_overflow=20,    
)


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()