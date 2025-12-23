# src/core/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class InterestQuery(BaseModel):
    """
    Represents an interest rate query with all necessary details.
    """
    query_type: str = Field(..., description="Type of query: 'savings', 'loan', 'card', 'general'")
    # --- THÊM TRƯỜNG PRODUCT ---
    product: Optional[str] = Field(None, description="Product name (e.g., 'Tiết kiệm thường')")
    # ---------------------------
    amount: Optional[float] = Field(None, description="Amount in VND")
    amount_text: Optional[str] = Field(None, description="Original amount text")
    term: Optional[str] = Field(None, description="Term (e.g., '6 months', '1 year')")
    # Thêm alias term_text để tương thích với code cũ nếu cần
    term_text: Optional[str] = Field(None, alias="term", description="Alias for term")
    is_online: Optional[bool] = Field(False, description="Is this an online transaction?")
    channel: Optional[str] = Field("online", description="Channel: 'online' or 'counter'") # Thêm trường channel cho rõ ràng
    loan_type: Optional[str] = Field(None, description="Type of loan (if applicable)")
    term_years: Optional[float] = Field(None, description="Loan term in years (if applicable)")
    # Thêm các trường tương thích khác nếu cần
    principal: Optional[float] = Field(None, description="Alias for amount (loan principal)")
    annual_rate_percent: Optional[float] = Field(None, description="Interest rate %/year")

    @validator('amount', pre=True, always=True)
    def parse_amount(cls, v, values):
        if v is not None:
            return v
        # Ưu tiên lấy từ 'principal' nếu có
        if 'principal' in values and values['principal'] is not None:
             return values['principal']
        if 'amount_text' in values and values['amount_text']:
            return cls._parse_vietnamese_number(values['amount_text'])
        return None

    @validator('principal', pre=True, always=True)
    def set_principal_alias(cls, v, values):
        # Đảm bảo principal và amount đồng bộ
        if v is not None: return v
        return values.get('amount')

    @validator('channel', pre=True, always=True)
    def set_channel_from_is_online(cls, v, values):
        if v is not None: return v
        return "online" if values.get("is_online") else "counter"

    # ... (giữ nguyên các phương thức _parse_vietnamese_number và _parse_term_to_years cũ của bạn)
    @staticmethod
    def _parse_vietnamese_number(text: str) -> Optional[float]:
        """Parse Vietnamese number format (e.g., '100 triệu', '1.5 tỷ') to float"""
        if not text or not isinstance(text, str):
            return None
        text = text.lower().strip()
        # (Logic parse giữ nguyên như file gốc của bạn)
        # ...
        return 0.0 # Placeholder, bạn copy lại logic cũ vào đây

    @staticmethod
    def _parse_term_to_years(term: str) -> float:
        # (Logic parse giữ nguyên như file gốc của bạn)
        return 0.0 # Placeholder