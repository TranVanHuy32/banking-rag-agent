# src/generation/query_parser.py
from __future__ import annotations
import logging
import re
from typing import Optional, List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage

# Import InterestQuery (Giữ nguyên logic cũ)
try:
    from src.models.interest import InterestQuery
except ImportError:
    from pydantic import BaseModel, Field
    class InterestQuery(BaseModel):  # type: ignore
        query_type: Optional[str] = Field(default=None)
        product: Optional[str] = None
        loan_type: Optional[str] = None
        term_text: Optional[str] = None
        term_years: Optional[float] = None
        principal: Optional[float] = None
        annual_rate_percent: Optional[float] = None
        channel: Optional[str] = "online"
        amount: Optional[float] = None

logger = logging.getLogger(__name__)

class QueryParser:
    def __init__(self, llm):
        self.structured_llm = llm.with_structured_output(InterestQuery)
        
        # [TỐI ƯU TỐC ĐỘ] Định nghĩa Fast Path bằng Regex
        # Các Key ở đây PHẢI KHỚP với danh sách trong ingest_data.py:
        # ["card", "loan", "savings", "promo", "digital-banking", "network", "faq", "general"]
        self.keyword_map = {
            "card": [r"(?i)\b(thẻ|credit card|visa|mastercard|jcb|napas)\b"],
            
            "loan": [r"(?i)\b(vay|lãi suất vay|cho vay|tín dụng)\b"],
            
            "savings": [r"(?i)\b(tiết kiệm|gửi tiền|lãi suất gửi|huy động)\b"],
            
            "promo": [r"(?i)\b(khuyến mãi|ưu đãi|giảm giá|voucher|quà tặng)\b"],
            
            "security": [r"(?i)\b(bảo mật|dữ liệu cung cấp |hệ thống bảo mật|thông tin)\b"],
            
            "digital-banking": [r"(?i)\b(app|ứng dụng|internet banking|digital|ngân hàng số|mật khẩu|đăng nhập|otp)\b"],
            
            "network": [r"(?i)\b(atm|chi nhánh|phòng giao dịch|địa điểm|giờ làm việc)\b"],
            
            "faq": [r"(?i)\b(câu hỏi thường gặp|hướng dẫn|quy trình|thủ tục)\b"],
            
            "general": [r"(?i)\b(xin chào|hello|hi|giới thiệu|liên hệ)\b"],

            "exchange_rate": [r"(?i)\b(tỷ giá|ngoại tệ|usd|eur|jpy|đô la|yên nhật|bảng anh|đổi tiền)\b"],
            
            "gold_price": [r"(?i)\b(giá vàng|vàng sjc|vàng 9999|vàng miếng)\b"],
        }

        # System Prompt (Giữ nguyên để dùng khi cần LLM xử lý câu phức tạp)
        self.system_prompt = (
            "Bạn là bộ não quản lý trạng thái hội thoại (State Manager).\n"
            "NHIỆM VỤ: Cập nhật JSON trạng thái dựa trên câu nói mới nhất của người dùng.\n\n"
            "CÁC LOẠI QUERY (query_type) BẮT BUỘC:\n"
            "- 'loan': Vay vốn.\n"
            "- 'savings': Tiết kiệm.\n"
            "- 'savings_goal': Mục tiêu tiết kiệm.\n"
            "- 'card': Thẻ.\n"
            "- 'promo': Khuyến mãi.\n"
            "- 'digital-banking': Ngân hàng số.\n"
            "- 'security': Bảo mật\n"
            "- 'network': Mạng lưới ATM, giờ làm việc.\n"
            "- 'faq': Câu hỏi thường gặp chung.\n"
            "- 'general': Thông tin chung khác.\n\n"
            "QUY TẮC loan_type:\n"
            "Nếu query_type='loan', hãy cố gắng xác định loan_type là: 'vay_mua_nha', 'vay_mua_oto', 'vay_tieu_dung_tin_chap', hoặc 'vay_kinh_doanh'.\n"
        )

    def _fast_classify(self, text: str) -> Optional[str]:
        """Hàm kiểm tra nhanh Regex để xác định query_type"""
        for q_type, patterns in self.keyword_map.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return q_type
        return None

    def _has_numbers(self, text: str) -> bool:
        """Kiểm tra xem câu có chứa con số (số tiền, kỳ hạn) không"""
        return bool(re.search(r'\d+', text))

    async def parse(self, current_text: str, current_state: Dict[str, Any] = {}) -> InterestQuery:
        # 1. [ƯU TIÊN TỐC ĐỘ] Fast Path
        # Nếu câu hỏi KHÔNG chứa số (chỉ hỏi thông tin chung) -> Dùng Regex
        # Ví dụ: "Lãi suất thẻ tín dụng bao nhiêu?" -> Regex bắt "thẻ" -> về 'card' ngay.
        has_number = self._has_numbers(current_text)
        fast_type = self._fast_classify(current_text)

        if fast_type and not has_number:
            logger.info(f"[QueryParser] Fast Path Triggered: '{current_text}' -> {fast_type}")
            # Nếu là 'loan' nhưng không có số, ta trả về loan object cơ bản
            # để RAG engine tìm kiếm trong kho 'loan'
            if fast_type == 'loan':
                 # Cố gắng đoán loan_type sơ bộ từ text để hỗ trợ RAG tốt hơn
                 l_type = None
                 if re.search(r"(?i)(nhà|đất|bất động sản)", current_text): l_type = "vay_mua_nha"
                 elif re.search(r"(?i)(xe|oto|ô tô)", current_text): l_type = "vay_mua_oto"
                 return InterestQuery(query_type="loan", loan_type=l_type)
            
            return InterestQuery(query_type=fast_type)

        # 2. [XỬ LÝ SÂU] Nếu có số hoặc Regex không bắt được -> Dùng LLM
        # Ví dụ: "Vay 500 triệu mua nhà" -> Có số -> Cần LLM trích xuất 'principal': 500000000
        logger.info(f"[QueryParser] Slow Path (LLM) Triggered: '{current_text}'")
        try:
            state_str = str(current_state) if current_state else "(Trạng thái rỗng)"
            full_prompt = (
                f"TRẠNG THÁI CŨ (JSON):\n{state_str}\n"
                "---------------------\n"
                f"USER INPUT MỚI: \"{current_text}\"\n"
                "---------------------\n"
                "YÊU CẦU: Trả về JSON trạng thái mới."
            )

            msg = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=full_prompt),
            ]
            resp = await self.structured_llm.ainvoke(msg)

            if isinstance(resp, dict):
                return InterestQuery(**resp)
            elif hasattr(resp, 'dict'): # Pydantic v1
                return resp
            elif hasattr(resp, 'model_dump'): # Pydantic v2
                return resp
            else:
                # Trường hợp fallback an toàn
                return InterestQuery(query_type="general")

        except Exception as e:
            logger.error(f"QueryParser CRITICAL ERROR: {e}", exc_info=True)
            return InterestQuery(query_type="general")