import json
import traceback
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import ChatRequest
from app.services.chat_service import handle_chat_stream

router = APIRouter()

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming chat endpoint.
    Hataları detaylıca konsola basan ve takılmaları önleyen teşhis sürümü.
    """
    async def event_generator():
        try:
            # İsteğin backend'e düştüğünü görelim ki "Beklemede" sorununun nerede tıkandığını anlayalım
            print(f"\n---> 🚀 YENİ İSTEK GELDİ (Müşteri: {request.customer_id})")
            
            async for event in handle_chat_stream(request, db):
                yield event
                
        except Exception as e:
            # 🔥 İŞTE BİZE GERÇEK HATAYI (DOSYA VE SATIR NUMARASINI) SÖYLEYECEK KISIM BURASI:
            print("\n" + "🔥"*25)
            print("💥 HATA TAM OLARAK BURADA PATLIYOR:")
            traceback.print_exc()  # Tüm hata yolunu terminale basar!
            print("🔥"*25 + "\n")
            
            # Tarayıcının "Beklemede" (Pending) kalıp kilitlenmesini engellemek için hata event'i dönüyoruz
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            print("---> 🛑 İŞLEM SONLANDI VEYA BAĞLANTI KOPTU\n")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",  # Beklemede kalmayı önleyen kritik header
            "X-Accel-Buffering": "no",
        },
    )