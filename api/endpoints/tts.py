# api/endpoints/tts.py
from fastapi import APIRouter, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
import logging

from src.services.tts_service import TTSService, TTSConfig

router = APIRouter()
logger = logging.getLogger(__name__)

class TTSRequest(BaseModel):
    """
    Đây là schema Pydantic cho request body.
    """
    text: str = Field(..., min_length=1, description="Văn bản tiếng Việt cần đọc")
    language_code: str = Field("vi-VN", description="Mã ngôn ngữ, mặc định vi-VN")
    voice_name: str | None = Field(None, description="Tên giọng, ví dụ: vi-VN-Standard-A (nữ)")
    speaking_rate: float = Field(1.0, ge=0.25, le=4.0)
    pitch: float = Field(0.0, ge=-20.0, le=20.0)
    audio_encoding: str = Field("MP3", description="MP3 | LINEAR16 | OGG_OPUS")
    provider: str | None = Field(None, description="google | gtts | auto")


@router.post("/speak", summary="Tổng hợp giọng nói tiếng Việt", tags=["TTS"], response_class=Response)
# Chuyển sang 'async def' để không block server
async def speak(req: TTSRequest):
    try:
        # 1. Tạo config từ request
        cfg = TTSConfig(
            provider=req.provider,
            language_code=req.language_code,
            voice_name=req.voice_name,
            speaking_rate=req.speaking_rate,
            pitch=req.pitch,
            audio_encoding=req.audio_encoding,
        )
        
        # 2. Khởi tạo service
        service = TTSService(cfg)
        
        # 3. Chạy hàm 'synthesize' (blocking) trong threadpool
        #    để không làm treo server.
        audio_bytes = await run_in_threadpool(service.synthesize, req.text)
        
        # 4. Trả về audio
        content_type = "audio/mpeg" if req.audio_encoding.upper() == "MP3" else (
            "audio/ogg" if req.audio_encoding.upper() == "OGG_OPUS" else "audio/wav"
        )
        return Response(content=audio_bytes, media_type=content_type)
        
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")