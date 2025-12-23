# src/retrieval/rerank_service.py
from __future__ import annotations
from typing import List
import logging
from pathlib import Path # Đảm bảo đã import
from langchain_core.documents import Document
from flashrank import Ranker, RerankRequest
from config.config import settings

logger = logging.getLogger(__name__)

class RerankService:
    def __init__(self):
        # [SỬA LỖI ĐƯỜNG DẪN] Chuyển BASE_DIR thành đối tượng Path
        # và tạo thư mục con 'models' bên trong nó
        model_cache = Path(settings.BASE_DIR) / "models_cache" / "reranker"
        
        # Tạo thư mục cache nếu chưa có
        model_cache.mkdir(parents=True, exist_ok=True)
        logger.info(f"Flashrank cache directory: {model_cache}")

        self.ranker = Ranker(model_name=settings.RERANK_MODEL, cache_dir=str(model_cache))
        logger.info(f"Flashrank initiated with model {settings.RERANK_MODEL}")

    def rerank(self, query: str, docs: List[Document], top_n: int = 3) -> List[Document]:
        if not docs: return []

        passages = [
            {"id": str(i), "text": d.page_content, "meta": d.metadata}
            for i, d in enumerate(docs)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_request)

        # Chỉ lấy top_n và lọc các kết quả có điểm > 0 (nếu cần)
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

        reranked_docs = []
        for res in sorted_results:
            doc = Document(page_content=res["text"], metadata=res["meta"])
            doc.metadata["rerank_score"] = res["score"]
            reranked_docs.append(doc)

        return reranked_docs

_reranker = None
def get_rerank_service():
    global _reranker
    if not _reranker:
        _reranker = RerankService()
    return _reranker