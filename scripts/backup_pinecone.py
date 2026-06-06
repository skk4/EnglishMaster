"""
备份 Pinecone 所有向量到本地 JSON 文件。

输出：data/backups/pinecone_backup_YYYYMMDD_HHMMSS.json
每个向量包含 id, values, metadata。
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

# 绕开代理（Pinecone 直连更稳定）
for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
    os.environ.pop(k, None)

BACKUP_DIR = Path("data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Connecting to Pinecone...")
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    idx = pc.Index(host=os.getenv("PINECONE_HOST"))

    stats = idx.describe_index_stats()
    total = stats.total_vector_count
    print(f"  Total vectors: {total}, Dimension: {stats.dimension}")

    # 收集所有 vector ID（list() 返回 ListItem 对象，取 .id 属性）
    print("Listing all vector IDs...")
    all_ids: list[str] = []
    for page in idx.list(prefix=""):
        all_ids.extend(item.id for item in page)
    print(f"  Found {len(all_ids)} IDs")

    # 分批 fetch + 写入（大 batch 减少 API 调用）
    BATCH = 100
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"pinecone_backup_{timestamp}.json"

    all_vectors = []
    for i in range(0, len(all_ids), BATCH):
        batch_ids = all_ids[i : i + BATCH]
        fetched = idx.fetch(ids=batch_ids)
        for vid, v in fetched.vectors.items():
            all_vectors.append({
                "id": vid,
                "values": v.values,
                "metadata": v.metadata,
            })
        print(f"  Fetched {min(i + BATCH, len(all_ids))}/{len(all_ids)}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_vectors, f, ensure_ascii=False)

    # 验证写入
    file_size = out_path.stat().st_size
    print(f"\n✅ Backup saved: {out_path}")
    print(f"   Vectors: {len(all_vectors)}")
    print(f"   File size: {file_size / 1024 / 1024:.1f} MB")

    # 快速校验
    print("\nUnit distribution (first 100):")
    units = {}
    for v in all_vectors[:100]:
        u = str(v["metadata"].get("unit", "?"))
        units[u] = units.get(u, 0) + 1
    for u in sorted(units, key=lambda x: (len(x), x)):
        print(f"  {u}: {units[u]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
