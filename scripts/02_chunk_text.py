"""
Step 02: Text Chunking

Input:  data/processed/raw_pages_semester{n}.json
Output: data/processed/chunks_semester{n}.json

Chunking strategy:
  - Split by sentences first (don't cut mid-sentence)
  - Target: 400 chars, Max: 600 chars, Overlap: 50 chars (last sentence of prev chunk)
  - Each chunk carries full metadata: page_num, unit, section, semester, char_count
  - Idempotent: skips output file if already exists (use --force to overwrite)
"""
import argparse
import json
import re
from pathlib import Path

MAX_CHUNK_SIZE    = 600
TARGET_CHUNK_SIZE = 400
OVERLAP_SIZE      = 50   # keep last sentence of previous chunk as overlap


def split_sentences(text: str) -> list[str]:
    """Split on English sentence boundaries and Chinese punctuation."""
    pattern = r'(?<=[.!?])\s+|(?<=[。！？\n])'
    parts = re.split(pattern, text)
    return [s.strip() for s in parts if s.strip()]


def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    chunk_idx = 0

    for page in pages:
        sentences = split_sentences(page["text"])
        current: list[str] = []
        current_size = 0

        for sentence in sentences:
            s_len = len(sentence)

            if current_size + s_len > MAX_CHUNK_SIZE and current:
                chunk_text = " ".join(current)
                chunks.append({
                    "chunk_id": f"s{page['semester']}_p{page['page_num']:03d}_c{chunk_idx:04d}",
                    "text": chunk_text,
                    "metadata": {
                        "page_num":   page["page_num"],
                        "unit":       page["unit"],
                        "section":    page["section"],
                        "semester":   page["semester"],
                        "char_count": len(chunk_text),
                    },
                })
                chunk_idx += 1

                # overlap: carry last sentence into next chunk
                if len(current) > 1:
                    current = [current[-1]]
                    current_size = len(current[0])
                else:
                    current = []
                    current_size = 0

            current.append(sentence)
            current_size += s_len

        # flush remaining sentences
        if current:
            chunk_text = " ".join(current)
            chunks.append({
                "chunk_id": f"s{page['semester']}_p{page['page_num']:03d}_c{chunk_idx:04d}",
                "text": chunk_text,
                "metadata": {
                    "page_num":   page["page_num"],
                    "unit":       page["unit"],
                    "section":    page["section"],
                    "semester":   page["semester"],
                    "char_count": len(chunk_text),
                },
            })
            chunk_idx += 1

    return chunks


def process_semester(semester: int, force: bool = False) -> int:
    input_path  = Path(f"data/processed/raw_pages_semester{semester}.json")
    output_path = Path(f"data/processed/chunks_semester{semester}.json")

    if not input_path.exists():
        print(f"  Semester {semester}: input not found, skipping.")
        return 0

    if output_path.exists() and not force:
        print(f"  Semester {semester}: output already exists, skipping (use --force to overwrite).")
        return 0

    with open(input_path, encoding="utf-8") as f:
        pages = json.load(f)

    chunks = chunk_pages(pages)

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    sizes = [c["metadata"]["char_count"] for c in chunks]
    print(f"  Semester {semester}: {len(pages)} pages → {len(chunks)} chunks")
    print(f"    size: min={min(sizes)}  max={max(sizes)}  avg={sum(sizes)//len(sizes)}")

    # unit breakdown
    unit_counts: dict[str, int] = {}
    for c in chunks:
        u = c["metadata"]["unit"]
        unit_counts[u] = unit_counts.get(u, 0) + 1
    for u in sorted(unit_counts, key=lambda x: (
            int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999, x)):
        print(f"    {u}: {unit_counts[u]} chunks")

    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="Chunk OCR text for RAG")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files")
    args = parser.parse_args()

    print("=" * 50)
    print("Step 02: Text Chunking")
    print("=" * 50)

    total = 0
    for semester in [1, 2]:
        total += process_semester(semester, force=args.force)

    print(f"\n✅ Total chunks: {total}")
    if total > 0:
        print("Next: python scripts/03_embed_and_upload.py")


if __name__ == "__main__":
    main()
