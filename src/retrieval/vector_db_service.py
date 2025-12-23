# src/retrieval/vector_db_service.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Any, Dict, Iterable
import logging
import asyncio

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS 
from config.config import settings

logger = logging.getLogger(__name__)

# --- Class _CombinedRetriever (để gộp kết quả từ nhiều kho) ---
class _CombinedRetriever:
    """Gộp kết quả từ nhiều retriever con (ví dụ: 'faq' + 'general')."""
    def __init__(self, retrievers: List[Any], final_k: int = 6):
        self.retrievers = [r for r in retrievers if r is not None]
        self.final_k = final_k
        
    def _uniq(self, docs: Iterable[Document]) -> List[Document]:
        seen, out = set(), []
        for d in docs:
            key = (d.page_content, d.metadata.get("source"))
            if key in seen: continue
            seen.add(key)
            out.append(d)
        return out

    async def ainvoke(self, query: str, **kwargs) -> List[Document]:
        """Chạy song song các retrievers."""
        tasks = [r.ainvoke(query, **kwargs) for r in self.retrievers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_docs = []
        for res in results:
            if not isinstance(res, Exception) and res:
                all_docs.extend(res)
        
        # Sắp xếp thô (cần Reranker để làm tốt hơn)
        return self._uniq(all_docs)[:self.final_k]

    def invoke(self, query: str, **kwargs) -> List[Document]:
        """Phiên bản Sync."""
        all_docs = []
        for r in self.retrievers:
            try: all_docs.extend(r.invoke(query, **kwargs) or [])
            except Exception: continue
        return self._uniq(all_docs)[:self.final_k]
# --- Hết class _CombinedRetriever ---


class VectorDBService:
    def __init__(self):
        self._emb = None
        # [SỬA] Cập nhật đầy đủ các domain mà ingest_data.py đã tạo
        self.domains = [
            "general", 
            "loan", 
            "savings", 
            "card", 
            "promo",
            "security",
            "digital-banking", 
            "network", 
            "faq"
        ]
        # Cache để lưu các kho FAISS (key là tên domain)
        self._db_cache: Dict[str, Optional[FAISS]] = {d: None for d in self.domains}

    @property
    def embeddings(self):
        """Sử dụng Google Embeddings."""
        if self._emb is None:
            logger.info(f"Đang tải Google Embedding model: {settings.GEMINI_EMBEDDING_MODEL}")
            self._emb = GoogleGenerativeAIEmbeddings(
                model=settings.GEMINI_EMBEDDING_MODEL,
                google_api_key=settings.GOOGLE_API_KEY
            )
        return self._emb

    def _load_db(self, domain: str) -> Optional[FAISS]:
        """Tải kho FAISS từ một thư mục domain cụ thể."""
        base_path = Path(settings.VECTOR_DB_PATH).resolve()
        domain_path = base_path / domain
        
        if not domain_path.exists():
            logger.warning(f"Chưa có dữ liệu Vector DB cho domain: '{domain}' tại {domain_path}")
            return None
        try:
            logger.info(f"Đang tải kho FAISS cho domain: '{domain}'...")
            return FAISS.load_local(
                folder_path=str(domain_path),
                index_name=settings.INDEX_NAME, # ví dụ: db_faiss.faiss
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as e:
            logger.error(f"Lỗi khi tải Vector DB '{domain}': {e}")
            return None

    def _get_db_instance(self, domain: str) -> Optional[FAISS]:
        """Lấy FAISS instance từ cache, nếu chưa có thì load."""
        if domain not in self._db_cache: 
            logger.warning(f"Domain '{domain}' không được hỗ trợ.")
            return None
        if self._db_cache[domain] is None:
            self._db_cache[domain] = self._load_db(domain)
        return self._db_cache[domain]

    def _create_retriever(self, db: Optional[FAISS], k: int, fetch_k: int, use_mmr: bool, score_threshold: Optional[float]):
        """Helper tạo retriever từ FAISS db."""
        if db is None: return None
        
        search_kwargs = {"k": k}
        search_type = "similarity"
        
        if use_mmr:
            search_type = "mmr"
            search_kwargs.update({"fetch_k": fetch_k})
        
        if score_threshold is not None:
            search_type = "similarity_score_threshold"
            search_kwargs["score_threshold"] = score_threshold

        return db.as_retriever(search_type=search_type, search_kwargs=search_kwargs)

    def get_retriever(self, 
                      domain: Optional[str] = None, 
                      k: int = 5, 
                      fetch_k: int = 20, 
                      use_mmr: bool = True, 
                      score_threshold: Optional[float] = None) -> Any:
        """
        [SỬA] Lấy retriever theo logic đa kho (Multi-domain).
        """
        k = settings.RETRIEVER_K
        fetch_k = settings.RETRIEVER_FETCH_K
        use_mmr = settings.RETRIEVER_USE_MMR
        score_threshold = settings.RETRIEVER_SCORE_THRESHOLD

        d = (domain or "general").lower().strip()
        
        # 1. Các kho "Độc lập" (chỉ tìm 1 mình nó)
        #   (Vay và Tiết kiệm rất chuyên biệt, không nên lẫn general)
        if d in ["loan", "savings"]:
            db = self._get_db_instance(d)
            return self._create_retriever(db, k, fetch_k, use_mmr, score_threshold)
            
        # 2. Các kho "Kết hợp" (cần tìm cả kho riêng VÀ kho 'general')
        #    Ví dụ: hỏi "thẻ" (card) nhưng cũng có thể liên quan đến "FAQ" (general)
        domains_to_search = [d]
        if d != "general":
             domains_to_search.append("general") # Luôn tìm thêm ở kho 'general'

        retrievers = []
        for dom in domains_to_search:
             db = self._get_db_instance(dom)
             # Lấy ít kết quả hơn từ mỗi kho con
             sub_k = k // len(domains_to_search) + 1 
             r = self._create_retriever(db, sub_k, fetch_k, use_mmr, score_threshold)
             if r: retrievers.append(r)
             
        if not retrievers:
            logger.warning(f"Không có Vector DB nào hoạt động cho domain '{d}' hoặc 'general'!")
            return None
        
        # Trả về retriever đã gộp
        return _CombinedRetriever(retrievers, final_k=k)

vector_db_service = VectorDBService()