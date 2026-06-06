import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app import models  
from app.api.v1.router import api_router

logger = logging.getLogger("app.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial data if tracking is enabled in configuration
    if settings.SEED_ON_STARTUP:
        try:
            from app.services.seed_service import seed_database
            async with AsyncSessionLocal() as session:
                await seed_database(session)
            logger.info("Database seeding process completed successfully.")
        except ImportError:
            logger.warning("seed_service.py module not found. Skipping initialization data seed.")
        except Exception as ex:
            logger.error(f"Unexpected error encountered during database seeding: {str(ex)}", exc_info=True)

    yield

    # Clean up connections and context on shutdown
    await engine.dispose()
    logger.info("Database engine resources successfully released.")


app = FastAPI(
    title="B2B Teklif Asistani API",
    version="1.0.0",
    lifespan=lifespan,
)
app.router.redirect_slashes = False
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register main API routing layer
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "llm_enabled": settings.llm_enabled,
        "model_configured": settings.OPENAI_MODEL
    }
    