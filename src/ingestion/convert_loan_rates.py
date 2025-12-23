# src/ingestion/convert_loan_rates.py
import json
import re
from pathlib import Path
import sys

# Cấu hình đường dẫn
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
DATA_DIR = project_root / "data"

def parse_loan_details(content: str) -> dict:
    """Trích xuất thông tin chi tiết từ nội dung của một loại vay"""
    details = {}
    
    # 1. Tìm thời hạn (ví dụ: Tối đa 25 năm)
    term_match = re.search(r"Thời hạn:.*?(\d+)\s*năm", content)
    if term_match:
        details["term_max_years"] = int(term_match.group(1))

    # 2. Tìm hạn mức
    limit_match = re.search(r"Hạn mức: (.*)", content)
    if limit_match:
        details["limit"] = limit_match.group(1).strip()

    # 3. Tìm lãi suất (ưu tiên lãi suất ưu đãi, sau đó lấy lãi suất đầu tiên)
    rate_match = re.search(r"Lãi suất (?:ưu đãi.*?)?:\s*([\d\.]+)", content)
    if rate_match:
        # Đây là lãi suất chính mà interest_calculator sẽ sử dụng
        details["Lãi suất ưu đãi"] = f"{rate_match.group(1)}%"
    
    # 4. Trích xuất toàn bộ mô tả lãi suất (cho RAG)
    rate_details = []
    promo_rate = re.search(r"(Lãi suất ưu đãi.*)", content)
    if promo_rate:
        rate_details.append(promo_rate.group(1).strip())
        
    after_promo_rate = re.search(r"(Lãi suất sau ưu đãi.*)", content)
    if after_promo_rate:
        rate_details.append(after_promo_rate.group(1).strip())
        
    # Nếu không có "ưu đãi", lấy lãi suất chung
    if not promo_rate and not after_promo_rate:
        flat_rate = re.search(r"(Lãi suất: .*?)(?=\n-|\n##|$)", content, re.DOTALL)
        if flat_rate:
            rate_details.append(flat_rate.group(1).strip())

    details["rate_details_text"] = ". ".join(rate_details)
    
    return details

def convert_loan_rates():
    """
    Chuyển đổi lai_suat_cho_vay.txt (Nguồn 31) thành loan_rates.json
    """
    input_file = DATA_DIR / "lai_suat_cho_vay.txt"
    output_file = DATA_DIR / "loan_rates.json"
    
    if not input_file.exists():
        print(f"Lỗi: Không tìm thấy file '{input_file.name}'")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    loan_rates_dict = {}
    
    # Tìm các mục con (ví dụ: ### 1.1 Vay mua nhà/đất)
    # cho đến khi gặp mục ## 4. (CHÍNH SÁCH ƯU ĐÃI)
    pattern = re.compile(r"### ([\d\.]+) (.*?)\n(.*?)(?=\n###|\n## 4\.)", re.DOTALL)
    
    matches = pattern.findall(content)
    
    if not matches:
        print("Lỗi: Không tìm thấy cấu trúc '###' nào trong file.")
        return

    print(f"Đang phân tích {input_file.name}...")
    for match in matches:
        loan_name = match[1].strip()
        details_content = match[2].strip()
        
        # Phân tích nội dung chi tiết
        details = parse_loan_details(details_content)
        
        # Lưu dưới dạng dictionary {tên_vay: {chi_tiết}}
        # để tương thích với interest_calculator.py (Nguồn 6)
        loan_rates_dict[loan_name] = details
        print(f"  + Đã xử lý: {loan_name}")

    # Ghi ra file JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(loan_rates_dict, f, ensure_ascii=False, indent=2)
        
    print(f"\nChuyển đổi thành công!")
    print(f"Đã lưu {len(loan_rates_dict)} loại vay vào: {output_file.name}")

if __name__ == "__main__":
    convert_loan_rates()