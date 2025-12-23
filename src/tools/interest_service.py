# src/tools/interest_service.py
from __future__ import annotations
import json
import re
import logging
import unicodedata
from math import isclose
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# --- 1. ĐỊNH NGHĨA MODEL (Tích hợp sẵn để không phụ thuộc file ngoài) ---
try:
    from src.models.interest import InterestQuery
except ImportError:
    # Fallback nếu không import được models
    from pydantic import BaseModel
    class InterestQuery(BaseModel): # type: ignore
        query_type: Optional[str] = None
        product: Optional[str] = None
        loan_type: Optional[str] = None
        term_text: Optional[str] = None
        term_years: Optional[float] = None
        principal: Optional[float] = None
        annual_rate_percent: Optional[float] = None
        channel: Optional[str] = "online"
        amount: Optional[float] = None

logger = logging.getLogger(__name__)

# Xác định đường dẫn data
try:
    from config.config import settings
    DATA_DIR_PATH = Path(settings.DATA_DIR).resolve()
except Exception:
    # Fallback đường dẫn tương đối nếu không load được config
    DATA_DIR_PATH = Path(__file__).resolve().parent.parent.parent / "data"

class InterestService:
    def __init__(self):
        self.data_dir = DATA_DIR_PATH
        logger.info(f"InterestService đang tải dữ liệu từ: {self.data_dir}")
        # Load dữ liệu ngay khi khởi tạo
        self.savings_rates = self._load_json(self.data_dir / "savings_rates.json")
        self.loan_rates = self._load_json(self.data_dir / "loan_rates.json")
        self.TERM_PAT = re.compile(r"(\d+)\s*(tháng|thang|thg|m|month|months|năm|nam|year|years)", re.I)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f: return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi đọc file {path.name}: {e}")
        return {}

    def _normalize_text(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
        return text.lower().strip()

    # ==================== LOGIC TÍNH TOÁN (Chuyển từ calculator sang) ====================
    def parse_term_months(self, text: str) -> int:
        if not text: return 0
        m = self.TERM_PAT.search(text)
        if not m: return 0
        val = int(m.group(1))
        unit = self._normalize_text(m.group(2))
        if unit in ("nam", "year", "years"): return val * 12
        return val

    # Trong class InterestService (file interest_service.py)

    def get_savings_rate(self, product: str, term_months: int, channel: str = "online") -> Tuple[Optional[float], int]:
        """
        Trả về: (Lãi suất tìm được, Kỳ hạn gốc được áp dụng)
        Ví dụ: Hỏi 15 tháng -> Trả về (Lãi suất 12 tháng, 12)
        """
        # 1. Tìm dữ liệu sản phẩm
        product_data = self.savings_rates.get(product)
        if not product_data:
             norm_product = self._normalize_text(product)
             for key, data in self.savings_rates.items():
                 if self._normalize_text(key) == norm_product:
                     product_data = data
                     break
        if not product_data: return (None, 0)

        # 2. Lấy danh sách các kỳ hạn có sẵn (dạng số nguyên)
        terms_map = product_data.get("terms") or {}
        # Chuyển keys từ str "12" sang int 12 và sắp xếp
        available_terms = sorted([int(k) for k in terms_map.keys()])

        # 3. Logic tìm kỳ hạn phù hợp (Step-down)
        applied_term = 0
        
        # Nếu kỳ hạn khách hỏi khớp chính xác
        if term_months in available_terms:
            applied_term = term_months
        else:
            # Tìm kỳ hạn lớn nhất mà vẫn nhỏ hơn kỳ hạn khách hỏi
            # Ví dụ: Khách hỏi 15, available=[12, 24]. Lấy 12.
            lower_terms = [t for t in available_terms if t < term_months]
            if lower_terms:
                applied_term = max(lower_terms)
            else:
                # Trường hợp hỏi kỳ hạn quá ngắn (nhỏ hơn kỳ hạn min của NH)
                # Thường sẽ trả về lãi không kỳ hạn (non-term)
                return (product_data.get("non_term", {}).get(channel, 0.1), 0)

        # 4. Lấy lãi suất của kỳ hạn đã chốt
        rate_info = terms_map.get(str(applied_term))
        rate = rate_info.get(channel) or rate_info.get("online" if channel == "counter" else "counter")
        
        return (rate, applied_term)

    def find_best_match_loan(self, text: str) -> Optional[str]:
        # Logic tìm gói vay
        if not text: return None
        norm_text = self._normalize_text(text)
        if norm_text in self.loan_rates: return norm_text
        
        for key, data in self.loan_rates.items():
            product_name = data.get("product_name", "")
            norm_name = self._normalize_text(product_name)
            keywords = re.findall(r'\b\w+\b', norm_name)
            for kw in keywords:
                if kw and kw != 'vay' and kw in norm_text: return key
        
        # Fallback các từ khóa cứng
        if 'nha' in norm_text: return 'vay_mua_nha'
        if 'oto' in norm_text or 'xe' in norm_text: return 'vay_mua_oto'
        if 'tieu dung' in norm_text or 'tin chap' in norm_text: return 'vay_tieu_dung_tin_chap'
        if 'bo sung von' in norm_text or 'von luu dong' in norm_text: return 'vay_kinh_doanh'
        return None

    # Hàm tính toán trả góp đều (EMI Formula)
    def _calc_loan_payment(self, principal, rate, years):
        if principal <= 0 or years <= 0: return 0
        
        # Chuyển đổi sang tháng
        r = (rate / 100.0) / 12.0  # Lãi suất tháng
        n = years * 12             # Tổng số tháng
        
        if r == 0: return principal / n
        
        # Công thức EMI: Trả cố định hàng tháng (Gốc + Lãi)
        # P * r * (1+r)^n / ((1+r)^n - 1)
        monthly_payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        return monthly_payment

    async def answer(self, q: InterestQuery) -> Tuple[Optional[str], List[Dict]]:
        try:
            # ==================== 1. XỬ LÝ VAY (LOAN) ====================
            if q.query_type == "loan":
                principal = q.principal or q.amount
                
                # Tìm gói vay phù hợp
                product_hint = q.loan_type or q.product or ""
                loan_key = self.find_best_match_loan(product_hint)
                
                # Lấy thông tin gói vay (hoặc mặc định)
                loan_info = self.loan_rates.get(loan_key, {}) if loan_key else {}
                loan_name = loan_info.get("product_name", "Vay tiêu dùng/Tín chấp")
                base_rate = loan_info.get("interest_rate")
                max_term = loan_info.get("max_term_years", 20)

                # [Case 1] Chưa có số tiền -> Tư vấn gói
                if not principal:
                    if loan_info:
                        return (f"🏦 **GÓI {loan_name.upper()}**\n"
                                f"📉 Lãi suất ưu đãi: từ **{base_rate}%/năm**\n"
                                f"⏳ Thời hạn vay tối đa: {max_term} năm\n"
                                f"📝 *{loan_info.get('details', '')}*\n\n"
                                f"💡 *Ví dụ: Bạn muốn vay 500 triệu trong 5 năm? Hãy nhập số tiền để mình tính thử nhé!*", [])
                    
                    # Nếu không rõ gói nào, liệt kê tất cả
                    msg = "🏦 **LÃI SUẤT CÁC GÓI VAY TIÊU BIỂU:**\n"
                    for k, v in self.loan_rates.items():
                        msg += f"🔹 **{v.get('product_name')}**: {v.get('interest_rate')}%/năm\n"
                    msg += "\n💬 *Bạn dự định vay bao nhiêu tiền?*"
                    return (msg, [])

                # [Case 2] Có số tiền -> Tính toán lịch trả nợ
                # Lãi suất: Ưu tiên user nhập -> Lãi gói vay -> Mặc định 12%
                final_rate = q.annual_rate_percent or base_rate or 12.0
                
                # Xử lý kỳ hạn
                term_years = q.term_years
                if not term_years and q.term_text:
                    months = self.parse_term_months(q.term_text)
                    if months > 0: term_years = months / 12.0
                
                if not term_years:
                    return (f"⏳ Với khoản vay **{principal:,.0f} VNĐ**, bạn muốn trả trong bao lâu (ví dụ: 3 năm, 60 tháng)?", [])

                # [Logic kiểm tra Max Term]
                if max_term and term_years > max_term:
                     return (f"⚠️ Gói **{loan_name}** chỉ hỗ trợ vay tối đa **{max_term} năm**.\n"
                             f"Bạn vui lòng chọn thời gian ngắn hơn nhé.", [])

                # Tính toán
                monthly_pay = self._calc_loan_payment(principal, final_rate, term_years)
                total_payment = monthly_pay * term_years * 12
                total_interest = total_payment - principal

                # [Quan trọng] Tạo Disclaimer về lãi suất thả nổi
                disclaimer = ""
                if final_rate < 10: # Thường lãi <10% là lãi ưu đãi
                    disclaimer = f"\n⚠️ *Lưu ý: Lãi suất {final_rate}% thường chỉ cố định trong 6-12 tháng đầu, sau đó sẽ thả nổi theo thị trường.*"

                msg = (
                    f"📋 **BẢNG TÍNH TRẢ GÓP (ƯỚC TÍNH)**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📦 Gói vay: **{loan_name}**\n"
                    f"💰 Số tiền: {principal:,.0f} VNĐ\n"
                    f"⏳ Thời hạn: {term_years} năm ({int(term_years*12)} tháng)\n"
                    f"📉 Lãi suất áp dụng: {final_rate}%/năm\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💸 **TRẢ HÀNG THÁNG:** {monthly_pay:,.0f} VNĐ\n"
                    f"*(Gồm gốc + lãi tính theo dư nợ giảm dần)*\n"
                    f"❗️ Tổng lãi dự kiến: {total_interest:,.0f} VNĐ\n"
                    f"{disclaimer}"
                )
                return (msg, [])

            # ... (Phần trên giữ nguyên)

            # --- 2. XỬ LÝ TIẾT KIỆM (SAVINGS) ---
            elif q.query_type == "savings":
                product = q.product or "Tiết kiệm thường"
                channel = (q.channel or "online").lower()
                principal = q.principal or q.amount
                
                # [SỬA LỖI] Không default tm = 12 ngay lập tức
                tm = 0 
                if q.term_text: tm = self.parse_term_months(q.term_text)
                elif q.term_years: tm = int(q.term_years * 12)

                # CASE A: Có số tiền -> Tính lãi (Lúc này mới cần default 12 nếu thiếu)
                if principal and principal > 0:
                    calc_tm = tm if tm > 0 else 12 # Nếu khách không nói kỳ hạn, mặc định tính thử 12 tháng
                    
                    rate, applied_term = self.get_savings_rate(product, calc_tm, channel)
                    
                    if rate is None: 
                         return (f"Hiện chưa có lãi suất chuẩn cho kỳ hạn **{calc_tm} tháng**. Bạn thử 6, 12 hoặc 24 tháng xem?", [])
                    
                    # Tính toán
                    years = calc_tm / 12.0
                    interest = principal * (rate / 100) * years
                    total = principal + interest
                    
                    note = ""
                    if applied_term > 0 and applied_term != calc_tm:
                        note = f"\n*(Áp dụng lãi suất của kỳ hạn {applied_term} tháng)*"

                    return (
                        f"🐖 **DỰ TÍNH TIẾT KIỆM**\n"
                        f"💵 Gửi: {principal:,.0f} VNĐ\n"
                        f"📅 Kỳ hạn: {calc_tm} tháng\n"
                        f"📉 Lãi suất: {rate}%/năm ({channel}){note}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"💰 **TIỀN LÃI:** +{interest:,.0f} VNĐ\n"
                        f"💎 **TỔNG VỀ:** {total:,.0f} VNĐ"
                    ), []

                # CASE B: Không có số tiền -> Tra cứu thông tin
                else:
                    # B.1: Khách hỏi kỳ hạn CỤ THỂ (Ví dụ: "Lãi 6 tháng bao nhiêu?")
                    if tm > 0:
                        rate, applied_term = self.get_savings_rate(product, tm, channel)
                        if rate:
                            note = ""
                            if applied_term > 0 and applied_term != tm:
                                 note = f" (áp dụng mức lãi của {applied_term} tháng)"
                            return (f"📈 Lãi suất kỳ hạn **{tm} tháng** ({channel}) là: **{rate}%/năm**{note}.", [])
                        else:
                            return (f"Hiện tại chưa có thông tin lãi suất cho kỳ hạn {tm} tháng.", [])
                    
                    # B.2: Khách hỏi CHUNG CHUNG -> Hiện BẢNG (Đây là cái bạn cần)
                    # Logic: tm == 0
                    product_data = self.savings_rates.get(product)
                    if not product_data:
                        # Thử tìm fallback nếu tên sản phẩm không khớp chính xác
                        for v in self.savings_rates.values():
                            product_data = v
                            break
                    
                    if product_data:
                        terms = product_data.get("terms", {})
                        # Sắp xếp kỳ hạn từ nhỏ đến lớn
                        sorted_terms = sorted(terms.items(), key=lambda x: int(x[0]))
                        
                        msg = f"📊 **BẢNG LÃI SUẤT TIẾT KIỆM ({channel.upper()})**\n"
                        msg += "━━━━━━━━━━━━━━━━━━\n"
                        
                        count = 0
                        for t, r_obj in sorted_terms:
                            r = r_obj.get(channel, 0)
                            # Chỉ hiện một số kỳ hạn tiêu biểu để bảng không quá dài
                            # Hoặc hiện hết nếu muốn
                            icon = "🔹"
                            if t in ["6", "12", "24", "36"]: icon = "⭐"
                            
                            msg += f"{icon} Kỳ hạn **{t} tháng**: **{r}%/năm**\n"
                            count += 1
                        
                        msg += "\n💬 *Bạn muốn tính thử lãi với số tiền cụ thể không?*"
                        return (msg, [])

            return (None, [])

        except Exception as e:
            logger.error(f"Service Error: {e}")
            return (None, [])

# Instance duy nhất để rag_engine import
interest_service = InterestService()