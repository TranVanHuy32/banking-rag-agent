# config/config.py
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _normalize_model(name: str) -> str:
    name = (name or "").strip()
    return name if name.startswith("models/") else f"models/{name}"

# 1. Tính toán BASE_DIR một lần duy nhất ở bên ngoài class
# (BASE_DIR = D:\banking-rag-agent)
BASE_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- BẮT BUỘC ---
    GOOGLE_API_KEY: str

    # --- CHỌN LLM PROVIDER ---
    LLM_PROVIDER: str = "gemini" 

    # --- MODEL NAMES ---
    GEMINI_EMBEDDING_MODEL: str = Field(default="models/text-embedding-004")
    GEMINI_CHAT_MODEL: str = Field(default="models/gemini-2.5-flash")

    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    RERANK_MODEL: str = Field(default="ms-marco-MiniLM-L-12-v2")
    RERANK_ENABLED: bool = True

    # --- [SỬA LỖI Ở ĐÂY] ---
    # 2. Sử dụng biến BASE_DIR_PATH đã tính toán
    BASE_DIR: str = Field(default=BASE_DIR_PATH)
    
    # 3. Sửa TẤT CẢ các default_factory để dùng BASE_DIR_PATH
    DATA_DIR: str = Field(default_factory=lambda: os.path.join(BASE_DIR_PATH, "data"))
    
    # [LỖI CŨ]: lambda: os.path.join(DATA_DIR, "raw")
    # [SỬA MỚI]:
    DATA_RAW_DIR: str = Field(default_factory=lambda: os.path.join(BASE_DIR_PATH, "data", "raw"))
    
    VECTOR_DB_PATH: str = Field(default_factory=lambda: os.path.join(BASE_DIR_PATH, "data", "vector_store", "chroma_db"))
    
    INDEX_NAME: str = Field(default="chroma.sqlite3")
    # -----------------

    # --- RAG TUNING ---
    RETRIEVER_K: int = 6
    RETRIEVER_FETCH_K: int = 20
    RETRIEVER_USE_MMR: bool = True
    RETRIEVER_SCORE_THRESHOLD: Optional[float] = None

    # --- UX / SESSION ---
    LLM_TEMPERATURE: float = 0.0
    SESSION_TTL: int = 3600
    SESSION_HISTORY_LENGTH: int = 10
    
    # --- LOGGING ---
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    ENVIRONMENT: str = "development"

    def __init__(self, **data):
        super().__init__(**data)
        # Các hàm chuẩn hóa này vẫn OK
        object.__setattr__(self, "GEMINI_EMBEDDING_MODEL", _normalize_model(self.GEMINI_EMBEDDING_MODEL))
        object.__setattr__(self, "GEMINI_CHAT_MODEL", _normalize_model(self.GEMINI_CHAT_MODEL))

settings = Settings()
