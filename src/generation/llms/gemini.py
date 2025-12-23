# src/generation/llms/gemini.py
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from config.config import settings

logger = logging.getLogger(__name__)

def build_gemini_llm(streaming: bool = True):
    """Khởi tạo và trả về một instance của ChatGoogleGenerativeAI."""
    logger.info(f"Building Gemini LLM: {settings.GEMINI_CHAT_MODEL}")
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_CHAT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        streaming=streaming,
        convert_system_message_to_human=True 
    )