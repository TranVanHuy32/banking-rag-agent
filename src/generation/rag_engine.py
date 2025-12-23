# src/generation/rag_engine.py
from __future__ import annotations
from typing import List, Dict, Optional, Any, AsyncGenerator
import logging
import uuid
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage

from config.config import settings
from src.retrieval.vector_db_service import vector_db_service 
from src.core.cache import cache
from src.generation.prompts import BANKING_RAG_PROMPT 
from src.generation.llm_builder import get_llm 

try:
    from src.generation.query_parser import QueryParser 
except ImportError:
    QueryParser = None
try:
    from src.tools.interest_service import interest_service 
except ImportError:
    interest_service = None

try:
    from src.tools.market_service import market_service 
except ImportError:
    market_service = None

logger = logging.getLogger(__name__)

class ConversationContext:
    def __init__(self, max_history: int = 5, ttl_seconds: int = 3600):
        self.max_history = max_history 
        self.ttl_seconds = ttl_seconds
    def _key_hist(self, session_id: str) -> str: return f"conv:{session_id}"
    def _key_state(self, session_id: str) -> str: return f"state:{session_id}"
    async def get_history_langchain(self, session_id: str) -> List[HumanMessage | AIMessage]:
        raw_hist = await self.get_history(session_id)
        messages = []
        for msg in raw_hist:
            if msg['role'] == 'user': messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant': messages.append(AIMessage(content=msg['content']))
        return messages
    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        data, _ = cache.get(self._key_hist(session_id))
        return list(data) if data and isinstance(data, list) else []
    async def add_history(self, session_id: str, role: str, content: str) -> None:
        history = await self.get_history(session_id)
        history.append({"role": role, "content": content, "ts": datetime.utcnow().isoformat()})
        history = history[-self.max_history:]
        cache.set(self._key_hist(session_id), history)
    def get_state(self, session_id: str) -> Dict[str, Any]:
        data, _ = cache.get(self._key_state(session_id))
        return data if isinstance(data, dict) else {}
    def save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        cache.set(self._key_state(session_id), state)

class RAGEngine:
    def __init__(self) -> None:
        self.ctx = ConversationContext()

        logger.info(f"Đang khởi tạo RAG Engine trên Raspberry Pi...")
        
        self.llm = get_llm(streaming=True)
        self.internal_llm = get_llm(streaming=False) 
        
        self._reranker = None
        self._use_rerank = False
        
        self._parser = QueryParser(self.internal_llm) if QueryParser else None
        
        logger.info("RAGEngine initialized (Optimized for Pi: No Rerank, Low Latency, Streaming Enabled).")

    async def start(self): logger.info("RAGEngine started.")
    async def shutdown(self): logger.info("RAGEngine stopped.")

    def _choose_retriever(self, query_type: Optional[str] = None) -> Any:
        domain_map = {
            "loan": "loan",
            "card": "card",
            "savings": "savings",
            "savings_goal": "savings", 
            "promo": "promo",
            "digital-banking": "digital-banking",
            "security": "security",
            "network": "network",
            "faq": "faq"
        }
        
        domain_to_search = domain_map.get(query_type, "general")
        logger.info(f"Routing query '{query_type}' -> Domain '{domain_to_search}'")
        return vector_db_service.get_retriever(domain=domain_to_search, k=3)

    async def _retrieve(self, question: str, retriever) -> List[Document]:
        if not retriever: return []
        try:
            docs = await retriever.ainvoke(question)
            return docs
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []

    async def chat(self, user_text: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        session_id = session_id or str(uuid.uuid4())
        current_state = self.ctx.get_state(session_id)
        await self.ctx.add_history(session_id, "user", user_text)

        query_type = "general"
        parsed_query = None

        # 1. PARSE
        if self._parser:
            try:
                parsed_query = await self._parser.parse(user_text, current_state)
                query_type = getattr(parsed_query, "query_type", "general") or "general"
                
                if parsed_query and query_type != 'general':
                     new_state = parsed_query.model_dump() if hasattr(parsed_query, 'model_dump') else parsed_query.dict()
                     self.ctx.save_state(session_id, new_state)
                     current_state = new_state
            except Exception as e: 
                logger.warning(f"Parser failed: {e}")

        # 2. TOOLS
        tool_answer = None
        tool_sources = []

        # 2.1 Tool: Interest Service
        if interest_service and query_type in {"loan", "savings", "savings_goal"} and parsed_query:
             try:
                answer, sources = await interest_service.answer(parsed_query)
                if answer:
                    tool_answer = answer
                    tool_sources = sources
             except Exception as e: logger.warning(f"InterestService warning: {e}")
        
        # 2.2 Tool: Market Service
        if not tool_answer and market_service and query_type in {"exchange_rate", "gold_price"}:
             try:
                answer, sources = await market_service.answer(query_type)
                if answer:
                    tool_answer = answer
                    tool_sources = sources
             except Exception as e: logger.warning(f"MarketService failed: {e}")

        # Nếu Tool trả lời được -> Yield luôn
        if tool_answer:
            yield tool_answer
            
            # Gửi nguồn tham khảo - ĐÃ TẮT ĐỂ TRÁNH ĐỌC
            # if tool_sources:
            #     yield "\n\nNguồn:\n"
            #     for src in tool_sources:
            #        yield f"- {src.get('source', 'Tài liệu')} (Trang {src.get('page', 'N/A')})\n"
            
            # Lưu lịch sử
            await self.ctx.add_history(session_id, "assistant", tool_answer)
            return

        # 3. RAG STREAMING
        retriever = self._choose_retriever(query_type)
        search_query = user_text 
        if len(user_text.split()) < 4 and isinstance(current_state, dict):
             product_hint = current_state.get("product") or current_state.get("loan_type")
             if product_hint: 
                 search_query = f"{product_hint} {user_text}"
        
        docs = await self._retrieve(search_query, retriever)
        context_text = "\n\n".join([d.page_content for d in docs]) if docs else ""
        chat_history = await self.ctx.get_history_langchain(session_id)

        rag_chain = BANKING_RAG_PROMPT | self.llm
        
        full_response = ""
        try:
            # STREAMING THỰC SỰ
            async for chunk in rag_chain.astream({
                "context": context_text,
                "chat_history": chat_history,
                "question": user_text 
            }):
                # Chunk thường là AIMessageChunk hoặc string
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                yield content
                full_response += content

        except Exception as e:
            logger.error(f"LLM Streaming error: {e}")
            err_msg = "\n[Lỗi kết nối hoặc xử lý]"
            yield err_msg
            full_response += err_msg

        # Nếu không có nội dung gì (LLM lỗi hoàn toàn)
        if not full_response:
            fallback = "Xin lỗi, tôi chưa tìm thấy thông tin chính xác trong hệ thống."
            yield fallback
            full_response = fallback

        # Yield nguồn tham khảo (cho RAG) - ĐÃ TẮT ĐỂ TRÁNH ĐỌC
        # if docs:
        #     yield "\n\nNguồn:\n"
        #     for d in docs:
        #         src = d.metadata.get('source', 'Tài liệu')
        #         page = d.metadata.get('page', 'N/A')
        #         yield f"- {src} (Trang {page})\n"

        # Lưu lịch sử
        await self.ctx.add_history(session_id, "assistant", full_response)

rag_engine = RAGEngine()
