"""
Qdrant VectorStore 实现（本地服务端）

为什么选 Qdrant：
- API 兼容 Pinecone（迁移零代码改动）
- 本地起 qdrant/qdrant docker 镜像即可
- 支持元数据过滤、分片、副本

启动 Qdrant：
    docker run -p 6333:6333 qdrant/qdrant

.env:
    VECTOR_STORE_TYPE=qdrant
    QDRANT_HOST=localhost
    QDRANT_PORT=6333

安装：
    pip install qdrant-client
"""
import logging
from typing import Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
except ImportError:
    raise ImportError("Run: pip install qdrant-client")

from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class QdrantStore(VectorStore):
    def __init__(self, client: QdrantClient, collection: str, dim: int = 1024):
        self.client = client
        self.collection = collection
        self.dim = dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            logger.info(f"Creating Qdrant collection '{self.collection}'")
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        must_conditions = []
        if filter_unit:
            must_conditions.append(FieldCondition(key="unit", match=MatchValue(value=filter_unit)))
        if filter_semester:
            must_conditions.append(FieldCondition(key="semester", match=MatchValue(value=filter_semester)))
        query_filter = Filter(must=must_conditions) if must_conditions else None

        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "metadata": r.payload,
            }
            for r in results
        ]

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        from qdrant_client.models import PointStruct
        points = [
            PointStruct(id=vid, vector=vec, payload=meta)
            for vid, vec, meta in zip(ids, embeddings, metadatas)
        ]
        # 分批 100
        for i in range(0, len(points), 100):
            self.client.upsert(self.collection, points=points[i : i + 100])

    def delete(self, ids: list[str]) -> None:
        self.client.delete(self.collection, points_selector={"ids": ids})

    def describe_stats(self) -> dict:
        info = self.client.get_collection(self.collection)
        return {
            "backend": "qdrant",
            "total_vector_count": info.points_count,
            "dimension": self.dim,
        }
