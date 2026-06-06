"""
RAG 服务 — VectorStore 抽象 + 两阶段检索（embedding 粗筛 + cross-encoder 重排序）。
"""
import logging
from typing import Optional

import torch
from sentence_transformers import CrossEncoder

from backend.config import get_settings
from backend.dependencies import get_embedding_model
from backend.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

# 中英文 cross-encoder，分辨"used to 怎么用"和"过去进行时"这类语义近但实际无关的 pair
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


class RAGService:
    def __init__(self):
        self.model = get_embedding_model()
        self.store = get_vector_store()
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.reranker = CrossEncoder(RERANKER_MODEL, device=device)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        """
        两阶段检索：
        1. embedding 粗筛 top_k * 3 个候选
        2. cross-encoder 重排序，只保留相关性分 > 0 的 top_k 个
        """
        top_k = top_k or settings.max_context_chunks

        # 阶段 1: embedding 粗筛
        query_embedding = self.model.encode(f"query: {query}").tolist()
        matches = self.store.query(
            query_embedding=query_embedding,
            top_k=top_k * 3,
            filter_unit=filter_unit,
            filter_semester=filter_semester,
        )

        if not matches:
            return []

        # 阶段 2: cross-encoder 重排序
        pairs = [(query, m["metadata"].get("text", "")) for m in matches]
        rerank_scores = self.reranker.predict(pairs).tolist()

        ranked = sorted(
            zip(matches, rerank_scores),
            key=lambda x: -x[1],
        )

        return [
            {
                "text":     m["metadata"].get("text", ""),
                "score":    round(float(score), 3),
                "unit":     m["metadata"].get("unit", ""),
                "section":  m["metadata"].get("section", ""),
                "page_num": m["metadata"].get("page_num", 0),
                "semester": m["metadata"].get("semester", 1),
            }
            for m, score in ranked[:top_k]
            if score > 0   # reranker 给负分 → 不相关，直接丢弃
        ]

    def format_context(self, chunks: list[dict]) -> str:
        if not chunks:
            return "No relevant textbook content found."
        parts = [
            f"[Source {i}: {c['unit']} {c['section']} (Page {c['page_num']}, Semester {c['semester']})]\n{c['text']}"
            for i, c in enumerate(chunks, 1)
        ]
        return "\n\n---\n\n".join(parts)
