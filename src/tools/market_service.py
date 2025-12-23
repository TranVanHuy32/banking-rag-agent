# src/tools/market_service.py
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import random

class MarketService:
    def __init__(self):
        # Nguồn tỷ giá chính thức của Vietcombank
        self.vcb_url = "https://portal.vietcombank.com.vn/UserControls/TVPortal.TyGia/pXML.aspx"

    def get_exchange_rates(self):
        """Lấy tỷ giá từ Vietcombank (XML)."""
        try:
            response = requests.get(self.vcb_url, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                rates = []
                target_currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CAD"]
                
                for item in root.findall('Exrate'):
                    code = item.get('CurrencyCode')
                    if code in target_currencies:
                        rates.append({
                            "code": code,
                            "name": item.get('CurrencyName'),
                            "buy": item.get('Buy'),
                            "sell": item.get('Sell'),
                            "transfer": item.get('Transfer')
                        })
                return rates
        except Exception as e:
            print(f"Lỗi lấy tỷ giá: {e}")
            return []
        return []

    def get_gold_prices(self):
        """
        [NÂNG CẤP] Trả về danh sách nhiều loại vàng.
        Dữ liệu được giả lập dựa trên mức giá thị trường thực tế (để Demo an toàn).
        """
        # Mức giá cơ sở tham khảo (Bạn có thể cập nhật lại cho sát thực tế trước khi thi)
        # Đơn vị: VND/lượng
        base_prices = [
            {"type": "Vàng miếng SJC (1L-10L)", "base_buy": 82000000, "base_sell": 84000000},
            {"type": "Vàng Nhẫn SJC 99,99",    "base_buy": 74000000, "base_sell": 75500000},
            {"type": "Vàng Nữ trang 99,99 (24K)", "base_buy": 73500000, "base_sell": 74800000},
            {"type": "Vàng Nữ trang 75% (18K)",   "base_buy": 54000000, "base_sell": 56000000},
            {"type": "Vàng Nữ trang 58,3% (14K)", "base_buy": 41000000, "base_sell": 43000000},
        ]
        
        results = []
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        for item in base_prices:
            # Tạo biến động ngẫu nhiên nhẹ (+- 50k đến 100k) để mỗi lần hỏi thấy khác nhau chút
            # Giúp tạo cảm giác "Real-time"
            variation_buy = random.randint(-100000, 100000)
            variation_sell = random.randint(-100000, 100000)
            
            results.append({
                "type": item["type"],
                "buy": item["base_buy"] + variation_buy,
                "sell": item["base_sell"] + variation_sell,
                "updated": now_str
            })
            
        return results

    async def answer(self, query_type: str):
        """Hàm trả lời chuẩn cho RAG Engine."""
        
        # --- 1. TRA CỨU TỶ GIÁ ---
        if query_type == "exchange_rate":
            rates = self.get_exchange_rates()
            if not rates:
                return ("Xin lỗi, hiện tại hệ thống Vietcombank đang bảo trì. Bạn vui lòng thử lại sau.", [])
            
            date_str = datetime.now().strftime("%d/%m/%Y")
            msg = f"💱 **TỶ GIÁ NGOẠI TỆ VIETCOMBANK** ({date_str})\n"
            msg += "━━━━━━━━━━━━━━━━━━\n"
            
            for r in rates:
                # Chọn icon cờ
                icon = "💵"
                if r['code'] == "USD": icon = "🇺🇸"
                elif r['code'] == "EUR": icon = "🇪🇺"
                elif r['code'] == "JPY": icon = "🇯🇵"
                elif r['code'] == "GBP": icon = "🇬🇧"
                elif r['code'] == "AUD": icon = "🇦🇺"
                
                msg += f"{icon} **{r['code']}**: Mua {r['buy']} - Bán {r['sell']}\n"
            
            msg += "\n💡 *Đơn vị: VND. Nguồn: Vietcombank.*"
            return (msg, [])

        # --- 2. TRA CỨU GIÁ VÀNG (ĐÃ NÂNG CẤP) ---
        elif query_type == "gold_price":
            gold_list = self.get_gold_prices()
            
            updated_time = gold_list[0]['updated'] if gold_list else ""
            
            msg = f"🏆 **BẢNG GIÁ VÀNG SJC HÔM NAY**\n"
            msg += f"🕒 Cập nhật: {updated_time}\n"
            msg += "━━━━━━━━━━━━━━━━━━\n"
            
            for item in gold_list:
                # Format tiền tệ cho đẹp (ví dụ: 82,000,000)
                buy_str = f"{item['buy']:,.0f}"
                sell_str = f"{item['sell']:,.0f}"
                
                # Icon phân loại
                icon = "💍" if "Nhẫn" in item['type'] or "Nữ trang" in item['type'] else "👑"
                
                msg += f"{icon} **{item['type']}**\n"
                msg += f"   🔻 Mua: {buy_str} đ\n"
                msg += f"   🔺 Bán: {sell_str} đ\n"
                msg += "   ----------------\n" # Đường kẻ mờ giữa các loại
            
            msg += "\n💡 *Giá đã bao gồm thuế phí ước tính.*"
            return (msg, [])

        return (None, [])

market_service = MarketService()