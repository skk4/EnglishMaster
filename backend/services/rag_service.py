"""
RAG 服务 — VectorStore 抽象 + 业务逻辑。

设计上把"向量存储"和"嵌入"分开：
- vector_store: 抽象层（可换 Pinecone/FAISS/Qdrant）
- embedding_model: sentence-transformers 本地
"""
import logging
from typing import Optional

from backend.config import get_settings
from backend.dependencies import get_embedding_model
from backend.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    def __init__(self):
        self.model = get_embedding_model()
        self.store = get_vector_store()  # 自动选 Pinecone/FAISS/Qdrant/...

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks.
        ⚠️ E5 rule: query must be prefixed with "query: "
        """
        top_k = top_k or settings.max_context_chunks
        query_embedding = self.model.encode(f"query: {query}").tolist()

        # 抽象层 filter 统一为 {field: value} 简单字典
        filter_dict: dict = {}
        if filter_unit:
            filter_dict["unit"] = filter_unit
        if filter_semester:
            filter_dict["semester"] = filter_semester

        # 调用抽象接口（不直接用 Pinecone）
        matches = self.store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_unit=filter_unit,
            filter_semester=filter_semester,
        )

        return [
            {
                "text":     m["metadata"].get("text", ""),
                "score":    m["score"],
                "unit":     m["metadata"].get("unit", ""),
                "section":  m["metadata"].get("section", ""),
                "page_num": m["metadata"].get("page_num", 0),
                "semester": m["metadata"].get("semester", 1),
            }
            for m in matches
            if m["score"] >= 0.3
        ]

    def format_context(self, chunks: list[dict]) -> str:
        if not chunks:
            return "No relevant textbook content found."
        parts = [
            f"[Source {i}: {c['unit']} {c['section']} (Page {c['page_num']}, Semester {c['semester']})]\n{c['text']}"
            for i, c in enumerate(chunks, 1)
        ]
        return "\n\n---\n\n".join(parts)
