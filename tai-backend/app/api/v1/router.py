from fastapi import APIRouter
from app.api.v1.endpoints import chat, products, knowledge, quotes, sessions

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
