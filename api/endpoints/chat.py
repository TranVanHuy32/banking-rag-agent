# api/endpoints/chat.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas.chat import ChatRequest
from src.generation.rag_engine import rag_engine
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/query", summary="Chat với AI Agent (Streaming)")
async def chat_endpoint(req: ChatRequest):
    try:
        session_id_to_use = req.session_id

        async def generate():
            # rag_engine.chat bây giờ là AsyncGenerator, trả về từng chunk text
            async for chunk in rag_engine.chat(req.question, session_id=session_id_to_use):
                yield chunk
            
            # Tín hiệu kết thúc stream cho Client biết
            yield "__END__"

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
