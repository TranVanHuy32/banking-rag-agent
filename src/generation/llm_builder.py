# src/generation/llm_builder.py
import logging
from config.config import settings
from src.generation.llms.gemini import build_gemini_llm

logger = logging.getLogger(__name__)

def get_llm(streaming: bool = True):
    """
    Hàm Factory: Đọc cấu hình và trả về LLM tương ứng.
    Hiện tại chỉ hỗ trợ Gemini.
    """
    provider = (settings.LLM_PROVIDER or "").lower()
    
    # Mặc định hoặc cấu hình rõ ràng là gemini
    if provider == 'gemini' or not provider:
        logger.info("LLM Factory: Selecting Gemini.")
        return build_gemini_llm(streaming)
        
    else:
        logger.warning(f"LLM Provider '{provider}' không được hỗ trợ. Đang chuyển về Gemini làm mặc định.")
        # Fallback về Gemini để đảm bảo ổn định
        return build_gemini_llm(streaming)
