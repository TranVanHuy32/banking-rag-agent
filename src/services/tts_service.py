# src/services/tts_service.py
from __future__ import annotations
import logging
from pydantic.v1 import BaseModel, Field

# Thư viện TTS bạn muốn dùng (ví dụ: Google, gTTS, etc.)
# Cài đặt: pip install google-cloud-texttospeech
try:
    from google.cloud import texttospeech
except ImportError:
    texttospeech = None  # type: ignore

logger = logging.getLogger(__name__)

class TTSConfig(BaseModel):
    """
    Đây là class cấu hình Pydantic mà file API (tts.py) cần.
    """
    provider: str | None = Field("auto", description="google | gtts | auto")
    language_code: str = Field("vi-VN", description="Mã ngôn ngữ")
    voice_name: str | None = Field("vi-VN-Standard-A", description="Tên giọng đọc")
    speaking_rate: float = Field(1.0, ge=0.25, le=4.0)
    pitch: float = Field(0.0, ge=-20.0, le=20.0)
    audio_encoding: str = Field("MP3", description="MP3 | LINEAR16 | OGG_OPUS")

    def get_google_encoding(self) -> Any:
        if texttospeech:
            if self.audio_encoding.upper() == "LINEAR16":
                return texttospeech.AudioEncoding.LINEAR16
            if self.audio_encoding.upper() == "OGG_OPUS":
                return texttospeech.AudioEncoding.OGG_OPUS
        return texttospeech.AudioEncoding.MP3  # Mặc định

class TTSService:
    """
    Đây là class service (logic) mà file API (tts.py) cần.
    Nó chứa logic thực sự để gọi API của Google hoặc thư viện khác.
    """
    def __init__(self, config: TTSConfig):
        self.config = config
        self.provider = config.provider
        
        # Ưu tiên Google Cloud TTS nếu đã cài đặt
        if self.provider == "auto" or self.provider == "google":
            if texttospeech is not None:
                try:
                    self.client = texttospeech.TextToSpeechClient()
                    self.provider = "google"
                except Exception as e:
                    logger.warning(f"Không thể khởi tạo Google TTS Client: {e}. Fallback sang gTTS.")
                    self.provider = "gtts"
            else:
                self.provider = "gtts"
        
        logger.info(f"TTSService đang dùng provider: {self.provider}")

    def synthesize(self, text: str) -> bytes:
        """
        Đây là hàm blocking (đồng bộ) thực hiện việc tạo âm thanh.
        FastAPI sẽ chạy hàm này trong một threadpool.
        """
        if self.provider == "google" and self.client:
            return self._synthesize_google(text)
        
        # Fallback (hoặc nếu chọn gTTS)
        # Cài đặt: pip install gTTS
        try:
            from gtts import gTTS
            from io import BytesIO
            
            tts = gTTS(text=text, lang=self.config.language_code.split('-')[0]) # gTTS dùng 'vi'
            mp3_fp = BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            return mp3_fp.read()
            
        except ImportError:
            logger.error("Provider 'gtts' được chọn nhưng chưa cài đặt 'pip install gTTS'")
            raise
        except Exception as e:
            logger.error(f"gTTS lỗi: {e}")
            raise

    def _synthesize_google(self, text: str) -> bytes:
        """Logic gọi Google Cloud TTS."""
        if not self.client:
            raise ValueError("Google TTS client chưa được khởi tạo.")
            
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=self.config.language_code,
            name=self.config.voice_name
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=self.config.get_google_encoding(),
            speaking_rate=self.config.speaking_rate,
            pitch=self.config.pitch
        )
        
        response = self.client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content