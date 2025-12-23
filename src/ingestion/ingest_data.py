# src/ingestion/ingest_data.py
import os
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

# --- CẤU HÌNH ĐƯỜNG DẪN ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent 
sys.path.append(str(project_root))

try:
    from config.config import settings 
except ImportError:
    print(f"[LỖI] Không thể import settings từ {project_root / 'config'}.")
    print("Hãy chắc chắn rằng file config.py của bạn nằm ở: D:\\banking-rag-agent\\config\\config.py")
    sys.exit(1)

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

# ====== ENV / PATH (Đọc từ settings) ======
DATA_DIR = Path(settings.DATA_RAW_DIR).resolve() # [SỬA] Đọc từ DATA_RAW_DIR
VECTOR_DB_PATH = Path(settings.VECTOR_DB_PATH).resolve() 
GOOGLE_API_KEY = settings.GOOGLE_API_KEY
GEMINI_EMBEDDING_MODEL = settings.GEMINI_EMBEDDING_MODEL
INDEX_NAME = settings.INDEX_NAME 

llm_classifier: Optional[ChatGoogleGenerativeAI] = None

# [MỚI] Định nghĩa tất cả các kho chuyên dụng
ALL_DOMAINS = ["card", "loan", "savings", "promo","security", "digital-banking", "network", "faq", "general"]

def init_classifier():
    global llm_classifier
    if GOOGLE_API_KEY:
        llm_classifier = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.0
        )

# --- (Các hàm parse_front_matter, clean_text, split_markdown_optimized giữ nguyên) ---
YAML_FRONT_MATTER = re.compile(r"(?s)^---\s*(.*?)\s*---\s*")
def parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    m = YAML_FRONT_MATTER.search(text)
    if not m: return {}, text
    raw, body = m.group(1), text[m.end():]
    meta: Dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body

def clean_text(raw: str) -> str:
    t = YAML_FRONT_MATTER.sub("", raw)
    t = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", t)
    t = re.sub(r"(?m)^(#{1,6})\s*#{1,6}\s*", r"\1 ", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def split_markdown_optimized(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[Document]:
    headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(text)
    recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", r"(?<=\. )", " ", ""])
    final_splits = recursive_splitter.split_documents(md_header_splits)
    return final_splits

def auto_classify_with_ai(text_snippet: str, fname: str) -> str:
    """Dùng AI (Gemini Flash) để đoán domain nếu metadata bị thiếu."""
    if not llm_classifier: return "general"
    try:
        snippet = text_snippet[:2500]
        # [MỚI] Cập nhật prompt AI với các domain mới
        prompt = (
            f"Phân loại tài liệu ngân hàng sau vào MỘT trong các nhóm: {ALL_DOMAINS}.\n"
            "- card: thẻ tín dụng, thẻ ghi nợ.\n"
            "- loan: các khoản vay, lãi suất vay.\n"
            "- savings: tiền gửi tiết kiệm, lãi suất huy động.\n"
            "- promo: các chương trình khuyến mãi, ưu đãi.\n"
            "- digital-banking: ngân hàng số, app mobile, internet banking, bảo mật online.\n"
            "- network: mạng lưới ATM, giờ làm việc chi nhánh.\n"
            "- faq: các câu hỏi thường gặp chung.\n"
            "- security: các câu hỏi về bảo mật, an toàn.\n"
            "- general: thông tin chung, chính sách, giới thiệu...\n"
            "Chỉ trả về 1 từ là tên nhóm (ví dụ: 'loan').\n\n"
            f"--- VĂN BẢN ({fname}) ---\n{snippet}\n--- HẾT ---\nPhân loại:"
        )
        resp = llm_classifier.invoke([HumanMessage(content=prompt)])
        cat = resp.content.strip().lower()
        
        if cat in ALL_DOMAINS:
            print(f"    (AI phân loại: '{fname}' -> {cat})")
            return cat
        print(f"    (AI trả về loại lạ '{cat}', fallback -> general)")
        return "general"
    except Exception as e:
        print(f"    (! Lỗi AI phân loại: {e}, fallback -> general)")
        return "general"

def guess_domain(meta: Dict[str, str], fname: str, raw_body: str = "") -> str:
    """Quyết định domain: Ưu tiên metadata, nếu không có thì dùng AI."""
    cat = (meta.get("category") or "").lower()
    
    # [MỚI] Thêm các category mới vào logic
    if cat in {"card","cards","account-card"}: return "card"
    if cat in {"loan","loan-rates","loan_rates"}: return "loan"
    if cat in {"saving","savings","deposit"}: return "savings"
    if cat in {"promo", "promotion", "khuyen_mai"}: return "promo"
    if cat in {"security", "privacy policy", "bao_mat"}: return "security"
    if cat in {"digital-banking", "digital"}: return "digital-banking"
    if cat in {"network", "atm", "branch"}: return "network"
    if cat in {"faq", "qna"}: return "faq"
    
    # Các file còn lại cho vào general
    if cat in {"fx", "remittance", "about", "general", "policy"}: return "general"
    
    # Nếu metadata trống, dùng AI để đoán
    if raw_body: 
        return auto_classify_with_ai(raw_body, fname)
        
    return "general"

# --- Các hàm nạp dữ liệu (Giữ nguyên) ---
def load_txt(path: Path) -> Tuple[List[Document], str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    fm, body = parse_front_matter(raw)
    dom = guess_domain(fm, path.name, raw_body=body)
    cleaned = clean_text(body)
    docs = split_markdown_optimized(cleaned)
    for d in docs:
        md = d.metadata or {}; md.update(fm); md["source"] = path.name; md["file"] = path.name; md["domain"] = dom
        d.metadata = md
    return docs, dom

def json_docs_from_loan_rates(path: Path) -> List[Document]:
    data = json.loads(path.read_text(encoding="utf-8"))
    docs: List[Document] = []
    for name, det in data.items():
        content = f"SẢN PHẨM VAY: {det.get('product_name', name)}\nLãi suất: {det.get('interest_rate')}%/năm\nKỳ hạn tối đa: {det.get('max_term_years')} năm\nChi tiết: {det.get('details')}"
        docs.append(Document(page_content=content, metadata={"source": path.name, "domain":"loan", "title":f"Lãi suất vay - {det.get('product_name', name)}"}))
    return docs

def json_docs_from_savings_rates(path: Path) -> List[Document]:
    data = json.loads(path.read_text(encoding="utf-8"))
    docs: List[Document] = []
    for pkey, det in data.items():
        lines = [f"SẢN PHẨM TIẾT KIỆM: {pkey}"]
        terms = det.get("terms",{})
        for t in ["1","3","6","12","24","36"]:
             if t in terms:
                 r = terms[t]
                 lines.append(f"Kỳ hạn {t} tháng: Online {r.get('online','—')}% / Quầy {r.get('counter','—')}%")
        docs.append(Document(page_content="\n".join(lines), metadata={"source": path.name, "domain":"savings","title":f"Lãi suất tiết kiệm - {pkey}"}))
    return docs

def build_store(docs: List[Document], emb: GoogleGenerativeAIEmbeddings) -> FAISS:
    if not docs: raise ValueError("Không có tài liệu để build FAISS")
    print(f"    Đang embedding {len(docs)} chunks...")
    store = FAISS.from_documents(docs, embedding=emb)
    return store

# --- HÀM CHÍNH ---
def main():
    print(f"--- BẮT ĐẦU QUÁ TRÌNH NẠP DỮ LIỆU (FAISS/GOOGLE) ---")
    print(f"Đọc dữ liệu từ: {DATA_DIR}")
    print(f"Lưu Vector DB vào: {VECTOR_DB_PATH}")
    if not GOOGLE_API_KEY:
        print("[LỖI] Thiếu GOOGLE_API_KEY. Vui lòng kiểm tra file .env")
        return

    emb = GoogleGenerativeAIEmbeddings(model=GEMINI_EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
    init_classifier()
    
    # [MỚI] Tạo các bucket tương ứng với ALL_DOMAINS
    buckets: Dict[str, List[Document]] = {domain: [] for domain in ALL_DOMAINS}

    # 1. Xử lý file .txt (Đọc từ DATA_RAW_DIR)
    txts = sorted(DATA_DIR.glob("*.txt"))
    print(f"\n[1/3] Đang xử lý {len(txts)} file .txt từ {DATA_DIR}...")
    for p in txts:
        try:
            print(f"  + Đang đọc '{p.name}'...")
            docs, dom = load_txt(p)
            if dom in buckets: buckets[dom].extend(docs)
            else: buckets["general"].extend(docs)
        except Exception as e: print(f"  ! Lỗi file {p.name}: {e}")

    # 2. Xử lý file JSON chuyên dụng
    print("\n[2/3] Đang xử lý file JSON chuyên dụng...")
    # JSON được đặt cùng cấp với thư mục 'raw' (tức là trong 'data/')
    json_data_dir = DATA_DIR.parent 
    lr = json_data_dir / "loan_rates.json"
    if lr.exists(): buckets["loan"].extend(json_docs_from_loan_rates(lr))
    sr = json_data_dir / "savings_rates.json"
    if sr.exists(): buckets["savings"].extend(json_docs_from_savings_rates(sr))
    print(f"  + Đã xử lý JSON.")

    # 3. Build và Lưu các kho FAISS
    print("\n[3/3] Đang tạo và lưu các Vector Index (FAISS)...")
    VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)

    for domain in ALL_DOMAINS: # Duyệt qua TẤT CẢ các domain
        docs_to_build = buckets[domain]
        if not docs_to_build:
            print(f"  - Bỏ qua domain '{domain}' (không có dữ liệu).")
            continue
        print(f"  -> Đang build domain '{domain}' với {len(docs_to_build)} chunks...")
        try:
            store = build_store(docs_to_build, emb)
            out_path = (VECTOR_DB_PATH / domain).resolve()
            out_path.mkdir(parents=True, exist_ok=True)
            store.save_local(folder_path=str(out_path), index_name=INDEX_NAME)
            print(f"     ✓ Đã lưu thành công vào: {out_path.name}/{INDEX_NAME}")
        except Exception as e: print(f"     ! Lỗi khi build/lưu domain '{domain}': {e}")

    print("\n--- HOÀN TẤT ---")

if __name__ == "__main__":
    main()