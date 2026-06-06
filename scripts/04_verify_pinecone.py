"""
Step 04: Verify Pinecone Retrieval

Checks index stats and runs test queries (Chinese + English) to confirm
the RAG pipeline is working end-to-end.

Pass criteria:
  - Total vectors >= 800
  - All test queries return at least 1 result with score >= 0.3
  - Both Chinese and English queries work

⚠️ E5 rule: query embeddings must use "query: " prefix
"""
import os

import torch
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
PINECONE_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_HOST   = os.getenv("PINECONE_HOST", "")
INDEX_NAME      = os.getenv("PINECONE_INDEX_NAME", "xsjkndb01")
MIN_VECTORS     = 800
MIN_SCORE       = 0.3

TEST_QUERIES = [
    # English
    ("EN", "What is the past tense of go?"),
    ("EN", "Unit 1 vocabulary words"),
    ("EN", "How to use comparative adjectives"),
    # Chinese
    ("CN", "第一单元的词汇"),
    ("CN", "过去时怎么用"),
    ("CN", "Grammar Focus 语法要点"),
]


def main():
    print("=" * 55)
    print("Step 04: Verify Pinecone Retrieval")
    print("=" * 55)

    # --- Connect ---
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(host=PINECONE_HOST) if PINECONE_HOST else pc.Index(INDEX_NAME)

    stats = index.describe_index_stats()
    total = stats.total_vector_count
    dim   = stats.dimension

    print(f"\n[Index stats]")
    print(f"  Name      : {INDEX_NAME}")
    print(f"  Dimension : {dim}  (expected 1024)")
    print(f"  Vectors   : {total}  (threshold >= {MIN_VECTORS})")
    vec_ok = total >= MIN_VECTORS and dim == 1024
    print(f"  {'✅' if vec_ok else '❌'} Index check {'PASSED' if vec_ok else 'FAILED'}")

    # --- Load model ---
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"\n[Embedding model]")
    print(f"  Loading {EMBEDDING_MODEL} on {device.upper()}...")
    model = SentenceTransformer(EMBEDDING_MODEL, device=device)
    print(f"  ✅ Ready")

    # --- Run test queries ---
    print(f"\n[Retrieval test — {len(TEST_QUERIES)} queries]")
    passed = 0

    for lang, query in TEST_QUERIES:
        # ⚠️ E5 rule: query prefix
        query_vec = model.encode(f"query: {query}").tolist()
        results = index.query(vector=query_vec, top_k=3, include_metadata=True)

        hits = [m for m in results.matches if m.score >= MIN_SCORE]
        ok = len(hits) > 0

        print(f"\n  [{lang}] \"{query}\"")
        if ok:
            passed += 1
            for m in hits:
                meta = m.metadata
                print(f"    ✅ score={m.score:.3f} | {meta.get('unit')} {meta.get('section')} | p{meta.get('page_num')} s{meta.get('semester')}")
                print(f"       {meta.get('text','')[:100]}...")
        else:
            print(f"    ❌ No results with score >= {MIN_SCORE}")
            if results.matches:
                top = results.matches[0]
                print(f"       (best score was {top.score:.3f})")

    # --- Metadata audit ---
    print(f"\n[Metadata audit]")
    VALID_UNITS = {f"Unit {i}" for i in range(1, 11)}
    bad_units = 0
    total_fetched = 0
    # 采样 100 个向量检查 metadata
    sample_ids = []
    for page in index.list(prefix=""):
        sample_ids.extend(item.id for item in page)
        if len(sample_ids) >= 100:
            break
    fetched = index.fetch(ids=sample_ids[:100])
    for vid, v in fetched.vectors.items():
        total_fetched += 1
        u = str(v.metadata.get("unit", "?"))
        if u not in VALID_UNITS:
            bad_units += 1
            print(f"    ❌ {vid}: unit={u} (bad)")
    meta_ok = bad_units == 0
    print(f"    {'✅' if meta_ok else '❌'} {total_fetched - bad_units}/{total_fetched} clean, {bad_units} bad")

    # --- Summary ---
    print(f"\n{'='*55}")
    all_ok = vec_ok and passed == len(TEST_QUERIES)
    print(f"Queries passed : {passed}/{len(TEST_QUERIES)}")
    print(f"Index check    : {'✅' if vec_ok else '❌'}")
    print()
    if all_ok:
        print("🎉 ALL CHECKS PASSED — Phase 0 complete!")
        print("   Pinecone xsjkndb01 is ready for the backend.")
        print("   Next phase: backend API (Phase 1)")
    else:
        print("⚠️  Some checks failed — review results above.")
        if passed < len(TEST_QUERIES):
            print("   Tip: low scores may mean E5 prefix is missing in 03_embed_and_upload.py")
    print("=" * 55)


if __name__ == "__main__":
    main()
