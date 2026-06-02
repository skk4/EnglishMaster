"""
pgvector VectorStore 实现（Postgres 扩展）

特点：
- 和现有数据库统一（如果迁到 PG）
- 单服务少一个
- 中等性能

.env:
    VECTOR_STORE_TYPE=pgvector
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

PG 表：
    CREATE EXTENSION vector;
    CREATE TABLE embeddings (
        id TEXT PRIMARY KEY,
        embedding VECTOR(1024),
        unit TEXT,
        section TEXT,
        page_num INT,
        semester INT,
        text TEXT
    );
"""
import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStore):
    def __init__(self, engine: AsyncEngine, dim: int = 1024):
        self.engine = engine
        self.dim = dim

    async def _ensure_table(self) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    embedding VECTOR({self.dim}),
                    metadata JSONB
                )
            """))

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        import asyncio
        return asyncio.run(self._query_async(query_embedding, top_k, filter_unit, filter_semester))

    async def _query_async(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_unit: Optional[str],
        filter_semester: Optional[int],
    ) -> list[dict]:
        await self._ensure_table()
        vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        where_parts = []
        params: dict = {"vec": vec_str, "limit": top_k}
        if filter_unit:
            where_parts.append("metadata->>'unit' = :unit")
            params["unit"] = filter_unit
        if filter_semester:
            where_parts.append("(metadata->>'semester')::int = :semester")
            params["semester"] = filter_semester
        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        sql = f"""
            SELECT id, metadata, 1 - (embedding <=> :vec) AS score
            FROM embeddings
            {where_clause}
            ORDER BY embedding <=> :vec
            LIMIT :limit
        """

        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql), params)
            rows = result.fetchall()

        return [
            {"id": r[0], "score": float(r[2]), "metadata": r[1] or {}}
            for r in rows
        ]

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        import asyncio
        asyncio.run(self._upsert_async(ids, embeddings, metadatas))

    async def _upsert_async(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        await self._ensure_table()
        async with self.engine.begin() as conn:
            for vid, vec, meta in zip(ids, embeddings, metadatas):
                vec_str = "[" + ",".join(str(x) for x in vec) + "]"
                await conn.execute(
                    text("""
                        INSERT INTO embeddings (id, embedding, metadata)
                        VALUES (:id, :vec, :meta)
                        ON CONFLICT (id) DO UPDATE SET embedding = :vec, metadata = :meta
                    """),
                    {"id": vid, "vec": vec_str, "meta": json.dumps(meta)},
                )

    def delete(self, ids: list[str]) -> None:
        import asyncio
        asyncio.run(self._delete_async(ids))

    async def _delete_async(self, ids: list[str]) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM embeddings WHERE id = ANY(:ids)"),
                {"ids": ids},
            )

    def describe_stats(self) -> dict:
        import asyncio
        return asyncio.run(self._stats_async())

    async def _stats_async(self) -> dict:
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM embeddings"))
            count = result.scalar()
        return {"backend": "pgvector", "total_vector_count": count, "dimension": self.dim}
