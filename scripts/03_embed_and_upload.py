"""
Step 03: Embed & Upload to Pinecone

Input:  data/processed/chunks_semester{n}.json
Output: Pinecone index xsjkndb01 (1024-dim, multilingual-e5-large)

Rules (AGENTS.md):
  - E5 prefix: documents use "passage: " prefix
  - Batch size: 100 vectors / batch, 0.5s sleep between batches
  - Retry: up to 3 attempts per batch (tenacity)
  - Pinecone: prefer Host direct connection over index name
  - Dimension check before upload
  - Idempotent: Pinecone upsert overwrites same ID

Estimated time: ~2-3 min on M1 (MPS acceleration)
"""
import json
import os
import time
from pathlib import Path

import torch
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

BATCH_SIZE      = 100
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
EMBEDDING_DIM   = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
PINECONE_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_HOST   = os.getenv("PINECONE_HOST", "")
INDEX_NAME      = os.getenv("PINECONE_INDEX_NAME", "xsjkndb01")


def load_model() -> SentenceTransformer:
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Loading {EMBEDDING_MODEL} on {device.upper()}...")
    model = SentenceTransformer(EMBEDDING_MODEL, device=device)

    # dimension sanity check before touching Pinecone
    test_vec = model.encode("passage: test")
    assert len(test_vec) == EMBEDDING_DIM, (
        f"Dimension mismatch: model outputs {len(test_vec)}, "
        f"expected {EMBEDDING_DIM}. Check EMBEDDING_MODEL in .env"
    )
    print(f"✅ Model ready — dim={len(test_vec)}, device={device.upper()}")
    return model


def connect_pinecone():
    pc = Pinecone(api_key=PINECONE_KEY)
    if PINECONE_HOST:
        index = pc.Index(host=PINECONE_HOST)
    else:
        index = pc.Index(INDEX_NAME)

    stats = index.describe_index_stats()
    print(f"✅ Pinecone connected: '{INDEX_NAME}'")
    print(f"   dim={stats.dimension}  existing vectors={stats.total_vector_count}")

    if stats.dimension != EMBEDDING_DIM:
        raise ValueError(
            f"Pinecone index dim={stats.dimension} != model dim={EMBEDDING_DIM}. "
            f"Set EMBEDDING_DIMENSION={stats.dimension} in .env"
        )
    return index


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def upsert_batch(index, vectors: list):
    index.upsert(vectors=vectors)


def load_all_chunks() -> list[dict]:
    all_chunks: list[dict] = []
    for semester in [1, 2]:
        path = Path(f"data/processed/chunks_semester{semester}.json")
        if path.exists():
            with open(path, encoding="utf-8") as f:
                chunks = json.load(f)
            all_chunks.extend(chunks)
            print(f"  Semester {semester}: {len(chunks)} chunks loaded")
    return all_chunks


def main():
    print("=" * 55)
    print("Step 03: Embed & Upload to Pinecone")
    print("=" * 55)

    model = load_model()
    index = connect_pinecone()
    chunks = load_all_chunks()
    print(f"\nTotal chunks to upload: {len(chunks)}")

    total_uploaded = 0
    start = time.time()

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]

        # ⚠️ E5 rule: document embeddings must use "passage: " prefix
        texts = [f"passage: {c['text']}" for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False)

        vectors = [
            {
                "id": c["chunk_id"],
                "values": emb.tolist(),
                "metadata": {
                    **c["metadata"],
                    "text": c["text"][:1000],  # Pinecone metadata size limit
                },
            }
            for c, emb in zip(batch, embeddings)
        ]

        upsert_batch(index, vectors)
        total_uploaded += len(vectors)
        pct = 100 * total_uploaded // len(chunks)
        elapsed = time.time() - start
        print(f"  [{total_uploaded:4d}/{len(chunks)}] {pct:3d}%  ({elapsed:.0f}s elapsed)")
        time.sleep(0.5)

    # wait for Pinecone to index
    time.sleep(3)
    stats = index.describe_index_stats()
    print(f"\n✅ Upload complete!")
    print(f"   Total vectors in '{INDEX_NAME}': {stats.total_vector_count}")
    print(f"   Time: {(time.time()-start)/60:.1f} min")
    print("\nNext: python scripts/04_verify_pinecone.py")


if __name__ == "__main__":
    main()
