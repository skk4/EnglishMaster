"""
Pinecone VectorStore 实现（默认，托管云）

原 backend/dependencies.py 里的逻辑迁移到这里。
"""
import logging
from typing import Optional

from pinecone import Pinecone

from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class PineconeStore(VectorStore):
    def __init__(self, api_key: str, host: str, index_name: str):
        if not api_key or not host:
            raise ValueError("PINECONE_API_KEY and PINECONE_HOST must be set")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(host=host)
        self.index_name = index_name

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        filter_dict: dict = {}
        if filter_unit:
            filter_dict["unit"] = {"$eq": filter_unit}
        if filter_semester:
            filter_dict["semester"] = {"$eq": filter_semester}

        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict or None,
        )
        return [
            {
                "id": m.id,
                "score": m.score,
                "metadata": m.metadata or {},
            }
            for m in results.matches
        ]

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        vectors = [
            {"id": i, "values": e, "metadata": m}
            for i, e, m in zip(ids, embeddings, metadatas)
        ]
        # 分批 100
        for i in range(0, len(vectors), 100):
            self.index.upsert(vectors=vectors[i : i + 100])

    def delete(self, ids: list[str]) -> None:
        self.index.delete(ids=ids)

    def describe_stats(self) -> dict:
        stats = self.index.describe_index_stats()
        return {
            "backend": "pinecone",
            "total_vector_count": stats.total_vector_count,
            "dimension": stats.dimension,
        }
