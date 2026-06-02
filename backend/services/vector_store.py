"""
Vector Store 抽象层

让 RAG 检索在 Pinecone / FAISS / Qdrant 之间可插拔。

用法：
    from backend.services.vector_store import get_vector_store

    store = get_vector_store()  # 根据 .env VECTOR_STORE_TYPE 自动选
    results = store.query("user query", top_k=5, filter_unit="Unit 1")
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStore(ABC):
    """向量存储抽象接口。"""

    @abstractmethod
    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        """
        返回 top_k 个最相似的 chunk，每个 dict 含：
        - id: 向量 ID
        - score: 相似度（0-1，越高越相似）
        - metadata: dict, 至少含 unit, section, page_num, semester, text
        """
        raise NotImplementedError

    @abstractmethod
    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """插入或更新向量。"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """删除向量。"""
        raise NotImplementedError

    @abstractmethod
    def describe_stats(self) -> dict:
        """返回索引状态（vector_count, dimension 等）。"""
        raise NotImplementedError

    def health_check(self) -> bool:
        """默认健康检查：调用 describe_stats 不抛异常。"""
        try:
            self.describe_stats()
            return True
        except Exception as e:
            logger.error(f"VectorStore health check failed: {e}")
            return False


# 延迟加载（避免启动时所有实现都 import）
_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """根据 .env VECTOR_STORE_TYPE 选择实现，单例。"""
    global _instance
    if _instance is not None:
        return _instance

    backend_type = os.getenv("VECTOR_STORE_TYPE", "pinecone").lower()
    logger.info(f"Initializing vector store: {backend_type}")

    if backend_type == "pinecone":
        from backend.services.pinecone_store import PineconeStore
        _instance = PineconeStore(
            api_key=settings.pinecone_api_key,
            host=settings.pinecone_host,
            index_name=settings.pinecone_index_name,
        )
    elif backend_type == "faiss":
        from backend.services.faiss_store import FAISSStore
        _instance = FAISSStore(
            index_path=os.getenv("FAISS_INDEX_PATH", "data/faiss_index"),
            dim=settings.embedding_dimension,
        )
    elif backend_type == "qdrant":
        from backend.services.qdrant_store import QdrantStore
        from qdrant_client import QdrantClient
        _instance = QdrantStore(
            client=QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", 6333)),
            ),
            collection=os.getenv("QDRANT_COLLECTION", "englishmaster"),
            dim=settings.embedding_dimension,
        )
    elif backend_type == "chroma":
        from backend.services.chroma_store import ChromaStore
        import chromadb
        _instance = ChromaStore(
            client=chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "data/chroma")),
            collection=os.getenv("CHROMA_COLLECTION", "englishmaster"),
        )
    elif backend_type == "pgvector":
        from backend.services.pgvector_store import PgVectorStore
        from sqlalchemy.ext.asyncio import create_async_engine
        _instance = PgVectorStore(
            engine=create_async_engine(os.getenv("DATABASE_URL")),
            dim=settings.embedding_dimension,
        )
    else:
        raise ValueError(f"Unknown VECTOR_STORE_TYPE: {backend_type}")

    return _instance


def reset_vector_store():
    """重置单例（测试用）。"""
    global _instance
    _instance = None
