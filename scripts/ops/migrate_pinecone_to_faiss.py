#!/usr/bin/env python3
"""
迁移 Pinecone → FAISS（本地化 RAG 的典型迁移路径）

用法：
    1. 备份 .env 中 VECTOR_STORE_TYPE=pinecone 时的索引（描述快照）
    2. 设 VECTOR_STORE_TYPE=faiss
    3. 跑本脚本：python scripts/ops/migrate_pinecone_to_faiss.py
    4. 验证：python scripts/04_verify_pinecone.py（即使名字带 pinecone，但已切到 faiss）

迁移数据：
- vector id
- 1024 维 embedding
- metadata（含 unit/section/page_num/semester/text）
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

import numpy as np

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

# 必须先以 pinecone 模式连，导出
os.environ["VECTOR_STORE_TYPE"] = "pinecone"

from backend.services.vector_store import get_vector_store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    logger.info("Step 1: 拉取 Pinecone 所有向量 + metadata")
    pinecone_store = get_vector_store()

    # 分批拉（100 一批）
    all_records = []
    batch_size = 100
    pagination_token = None

    while True:
        # 走底层 pinecone API（因为我们的抽象层没暴露 list）
        from pinecone import Pinecone
        from backend.config import get_settings
        s = get_settings()
        pc = Pinecone(api_key=s.pinecone_api_key)
        index = pc.Index(host=s.pinecone_host)

        kwargs = {"namespace": "", "limit": batch_size, "include_values": True, "include_metadata": True}
        if pagination_token:
            kwargs["pagination_token"] = pagination_token

        try:
            result = index.list_paginated(**kwargs)
        except AttributeError:
            # 旧版本
            ids = [v.id for v in index.list(**kwargs)]
            if not ids:
                break
            fetch = index.fetch(ids=ids)
            for vid, vec in fetch.vectors.items():
                all_records.append({"id": vid, "values": vec.values, "metadata": vec.metadata or {}})
            if len(ids) < batch_size:
                break
            continue

        vectors = result.vectors or []
        for v in vectors:
            all_records.append({
                "id": v.id,
                "values": v.values,
                "metadata": v.metadata or {},
            })
        logger.info(f"  Fetched {len(all_records)} so far...")

        if not result.pagination or not result.pagination.get("next"):
            break
        pagination_token = result.pagination["next"]

    logger.info(f"Step 2: 共拉取 {len(all_records)} 条")

    # 切到 FAISS 模式
    logger.info("Step 3: 切到 FAISS 模式，写入")
    os.environ["VECTOR_STORE_TYPE"] = "faiss"
    # 清单例
    from backend.services import vector_store as vs_module
    vs_module._instance = None

    faiss_store = get_vector_store()

    if not all_records:
        logger.warning("无数据可迁移")
        return

    ids = [r["id"] for r in all_records]
    vectors = [r["values"] for r in all_records]
    metadatas = [r["metadata"] for r in all_records]

    # FAISS upsert（如果实现支持）
    if hasattr(faiss_store, "upsert"):
        faiss_store.upsert(ids, vectors, metadatas)
    else:
        logger.error("FAISS store 没有 upsert 方法")
        return

    # 验证
    stats = faiss_store.describe_stats()
    logger.info(f"Step 4: 迁移完成: {stats}")

    # 跑 RAG 检索烟雾测试
    from backend.dependencies import get_embedding_model
    model = get_embedding_model()
    if model is not None:
        import asyncio
        from backend.services.vector_store import reset_vector_store
        # model 应已加载，但保险起见异步加载
        try:
            logger.info("Smoke test: 查 1 个 query")
            q_vec = model.encode("query: past continuous tense").tolist()
            results = faiss_store.query(q_vec, top_k=3)
            logger.info(f"  Got {len(results)} results, top score: {results[0]['score']:.3f}" if results else "  No results")
        except Exception as e:
            logger.warning(f"  Smoke test 失败（embedding model 未加载）: {e}")


if __name__ == "__main__":
    main()
