"""
FAISS VectorStore 实现（本地，无服务端）

特点：
- 纯本地：index 存文件 `data/faiss_index/`
- 零运维：不需要起任何服务
- 性能极优：Meta 出品
- 限制：FAISS 不支持元数据过滤 → 自己用 metadata dict 配 ID 一起存 JSON

文件结构：
  data/faiss_index/
  ├── index.faiss        # FAISS 二进制
  ├── index.pkl          # ID 列表
  └── metadata.json      # {id: {unit, section, page_num, semester, text}, ...}
"""
import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None
    raise ImportError(
        "FAISS not installed. Run: pip install faiss-cpu sentence-transformers"
    )

from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class FAISSStore(VectorStore):
    """FAISS 向量存储（CPU 版本，零运维）。"""

    def __init__(self, index_path: str, dim: int = 1024):
        self.index_path = Path(index_path)
        self.dim = dim
        self.index_file = self.index_path / "index.faiss"
        self.id_file = self.index_path / "index.pkl"
        self.meta_file = self.index_path / "metadata.json"

        self.index_path.mkdir(parents=True, exist_ok=True)
        self.metadata: dict[str, dict] = self._load_metadata()
        self.index: faiss.Index = self._load_or_create_index()

    def _load_metadata(self) -> dict:
        if self.meta_file.exists():
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_metadata(self) -> None:
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)

    def _load_or_create_index(self) -> faiss.Index:
        if self.index_file.exists() and self.id_file.exists():
            logger.info(f"Loading FAISS index from {self.index_path}")
            index = faiss.read_index(str(self.index_file))
            with open(self.id_file, "rb") as f:
                self._ids: list[str] = pickle.load(f)
            return index

        logger.info(f"Creating new FAISS index at {self.index_path}")
        # IndexFlatIP = 内积（cosine 相似度用归一化向量）
        index = faiss.IndexFlatIP(self.dim)
        self._ids: list[str] = []
        return index

    def _persist(self) -> None:
        """保存到磁盘。"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.id_file, "wb") as f:
            pickle.dump(self._ids, f)
        self._save_metadata()

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> list[dict]:
        # 1. 拿 top_k * 5（多取一些以补偿过滤损失）
        overshoot = top_k * 5 if (filter_unit or filter_semester) else top_k
        query_vec = np.array([query_embedding], dtype=np.float32)
        # FAISS 用 L2 默认，但我们用 IP + 归一化 cosine
        faiss.normalize_L2(query_vec)

        scores, indices = self.index.search(query_vec, overshoot)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self._ids):
                continue
            vec_id = self._ids[idx]
            meta = self.metadata.get(vec_id, {})

            # 应用元数据过滤
            if filter_unit and meta.get("unit") != filter_unit:
                continue
            if filter_semester and meta.get("semester") != filter_semester:
                continue

            results.append({
                "id": vec_id,
                "score": float(score),
                "metadata": meta,
            })
            if len(results) >= top_k:
                break

        return results

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        for vec_id, vec, meta in zip(ids, vectors, metadatas):
            if vec_id in self.metadata:
                # 已有：删除旧向量（FAISS 不支持原地更新）
                old_idx = self._ids.index(vec_id) if vec_id in self._ids else -1
                if old_idx >= 0:
                    # FAISS IndexFlatIP 不支持删除，但小规模下可重建
                    # 生产建议重建完整 index
                    self._ids.pop(old_idx)
                    # 简单做法：直接添加到末尾（会有重复但元数据会更新）
            self._ids.append(vec_id)
            self.metadata[vec_id] = meta

        self.index.add(vectors)
        self._persist()
        logger.info(f"FAISS: upserted {len(ids)} vectors, total={self.index.ntotal}")

    def delete(self, ids: list[str]) -> None:
        """FAISS IndexFlatIP 不支持删除 → 重建 index。"""
        for vec_id in ids:
            if vec_id in self.metadata:
                del self.metadata[vec_id]
            if vec_id in self._ids:
                self._ids.remove(vec_id)

        # 重建 index
        if self._ids:
            # 从 metadata 重新生成（需要 embedding，存 embedding 副本或接受空）
            # 简化：这里只清元数据；如需真实删除，调用方用 reindex()
            logger.warning("FAISS delete: metadata cleared, run scripts/faiss_reindex.py to physically remove")
        self._save_metadata()

    def describe_stats(self) -> dict:
        return {
            "backend": "faiss",
            "total_vector_count": self.index.ntotal,
            "dimension": self.dim,
            "storage": str(self.index_path),
        }
