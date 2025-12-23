# src/scripts/evaluate_data.py
import sys
import os
import time
from pathlib import Path

# --- CẤU HÌNH ĐƯỜNG DẪN ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

print(">>> Đang khởi động script đánh giá...", flush=True)

try:
    from config.config import settings
    print(f" [OK] Đã load cấu hình. DATA_RAW_DIR: {settings.DATA_RAW_DIR}", flush=True)
except Exception as e:
    print(f" [LỖI] Không thể load config: {e}", flush=True)
    sys.exit(1)

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.core.semantic_utils import calculate_cosine_similarity
# Tùy chọn: Dùng tqdm nếu có, không thì dùng range thường
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=""):
        print(f" (Không có tqdm, chạy chế độ đơn giản) - {desc}")
        return iterable

def run_evaluation():
    start_time = time.time()
    
    # --- BƯỚC 1: LOAD DỮ LIỆU ---
    print(f"\n1. [BẮT ĐẦU] Đọc dữ liệu từ: {settings.DATA_RAW_DIR}", flush=True)
    if not os.path.exists(settings.DATA_RAW_DIR):
        print(f" [LỖI GIẢI] Thư mục không tồn tại: {settings.DATA_RAW_DIR}", flush=True)
        return

    # Kiểm tra xem có file txt nào không
    txt_files = list(Path(settings.DATA_RAW_DIR).glob("**/*.txt"))
    print(f"   -> Tìm thấy {len(txt_files)} file .txt", flush=True)
    if len(txt_files) == 0:
        print("   [CẢNH BÁO] Không có file dữ liệu nào để xử lý!", flush=True)
        return

    loader = DirectoryLoader(settings.DATA_RAW_DIR, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    docs = loader.load()
    print(f"   -> Đã đọc nội dung của {len(docs)} tài liệu.", flush=True)

    print("   -> Đang chia nhỏ văn bản (Chunking)...", flush=True)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)
    print(f"   -> Đã tạo ra {len(chunks)} chunks.", flush=True)

    if len(chunks) == 0:
        print(" [DỪNG] Không có chunk nào để đánh giá.", flush=True)
        return

    # --- BƯỚC 2: LOAD MODEL ---
    print("\n2. [ĐANG TẢI MODEL] HuggingFaceEmbeddings (Lần đầu sẽ lâu do phải tải model về máy)...", flush=True)
    embeddings_model = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    print("   -> [OK] Model đã sẵn sàng!", flush=True)

    # --- BƯỚC 3: ĐÁNH GIÁ ---
    print("\n3. [BẮT ĐẦU] Đánh giá Semantic...", flush=True)
    good_chunks = 0
    bad_chunks = 0
    rejected_samples = []
    THRESHOLD = 0.5

    # Dùng set để tránh tính toán lại embedding cho cùng một doc nhiều lần
    processed_docs = {}

    for chunk in tqdm(chunks, desc="Tiến độ"):
        source = chunk.metadata.get('source')
        
        # Nếu doc này chưa được embed, hãy embed nó
        if source not in processed_docs:
            # Tìm doc gốc tương ứng
            original_doc = next((d for d in docs if d.metadata.get('source') == source), None)
            if original_doc:
                # Embed 1000 ký tự đầu làm đại diện
                processed_docs[source] = embeddings_model.embed_query(original_doc.page_content[:1000])
            else:
                processed_docs[source] = None # Không tìm thấy doc gốc (hiếm gặp)

        doc_embedding = processed_docs[source]
        if doc_embedding is None: continue

        # Embed chunk hiện tại
        chunk_embedding = embeddings_model.embed_query(chunk.page_content)
        
        # Tính điểm
        score = calculate_cosine_similarity(chunk_embedding, doc_embedding)

        if score >= THRESHOLD:
            good_chunks += 1
        else:
            bad_chunks += 1
            if len(rejected_samples) < 5: # Chỉ lưu 5 mẫu để review
                rejected_samples.append({
                    "score": score,
                    "source": Path(source).name,
                    "content": chunk.page_content.replace("\n", " ")[:80] + "..."
                })

    # --- BƯỚC 4: KẾT QUẢ ---
    total = good_chunks + bad_chunks
    print(f"\n=== KẾT QUẢ ĐÁNH GIÁ (Ngưỡng {THRESHOLD}) ===")
    print(f"⏱️ Thời gian chạy: {time.time() - start_time:.2f} giây")
    print(f"✅ Đạt yêu cầu: {good_chunks}/{total} ({(good_chunks/total)*100:.1f}%)")
    print(f"❌ Kém chất lượng: {bad_chunks}/{total} ({(bad_chunks/total)*100:.1f}%)")
    
    if rejected_samples:
        print("\n--- VÍ DỤ CHUNK BỊ LOẠI BỎ ---")
        for sample in rejected_samples:
            print(f"[{sample['score']:.2f}] {sample['source']}: {sample['content']}")

if __name__ == "__main__":
    run_evaluation()