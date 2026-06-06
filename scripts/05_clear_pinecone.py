"""
清空 Pinecone index 所有向量（保留 index 结构）。

⚠️ 不可逆操作！确认有备份后再执行。
"""
import os
import sys
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
for k in ("HTTPS_PROXY", "HTTP_PROXY"): os.environ.pop(k, None)


def main():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    idx = pc.Index(host=os.getenv("PINECONE_HOST"))

    stats = idx.describe_index_stats()
    total = stats.total_vector_count
    print(f"Index vectors: {total}")

    if total == 0:
        print("Already empty.")
        return 0

    print(f"Deleting all {total} vectors...")
    ids = []
    for page in idx.list(prefix=""):
        ids.extend(item.id for item in page)
    print(f"  Found {len(ids)} IDs")

    BATCH = 1000
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        idx.delete(ids=batch)
        print(f"  Deleted {min(i + BATCH, len(ids))}/{len(ids)}")

    stats = idx.describe_index_stats()
    assert stats.total_vector_count == 0, f"Still have {stats.total_vector_count} vectors!"
    print(f"✅ Index empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
