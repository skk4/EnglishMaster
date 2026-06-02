"""
Chroma VectorStore 实现（纯 Python，最易上手）

特点：
- 零配置：pip install 即可
- 持久化到本地文件夹
- 性能一般（<100k 向量够用）

.env:
    VECTOR_STORE_TYPE=chroma
    CHROMA_PATH=./data/chroma
"""
import logging
from typing import Optional

try:
    import chromadb
except ImportError:
    raise ImportError("Run: pip install chromadb")

from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ChromaStore(VectorStore):
    def __init__(self, client, collection: str, dim: int = 1024):
        self.client = client
        self.collection_name = collection
        self.dim = dim
        # get_or_create 不需要单独建表
        self.collection = client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        where = {}
        if filter_unit:
            where["unit"] = filter_unit
        if filter_semester:
            where["semester"] = filter_semester

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where if where else None,
        )

        out = []
        for i, vid in enumerate(results["ids"][0]):
            out.append({
                "id": vid,
                "score": 1 - results["distances"][0][i],  # cosine distance → similarity
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            })
        return out

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        # 分批 100
        for i in range(0, len(ids), 100):
            self.collection.upsert(
                ids=ids[i : i + 100],
                embeddings=embeddings[i : i + 100],
                metadatas=metadatas[i : i + 100],
            )

    def delete(self, ids: list[str]) -> None:
        self.collection.delete(ids=ids)

    def describe_stats(self) -> dict:
        return {
            "backend": "chroma",
            "total_vector_count": self.collection.count(),
            "dimension": self.dim,
        }
