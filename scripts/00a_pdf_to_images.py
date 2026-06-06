"""
Step 0a: PDF → Images (or direct text extraction for native PDFs)

Input:  data/raw/grade8_semester1.pdf  (241.8MB, scanned)
        data/raw/grade8_semester2.pdf  (10.7MB,  auto-detect)

Output (scanned PDF):
  data/images/semester{n}/page_NNN.png
  data/images/semester{n}_manifest.json

Output (native PDF):
  data/processed/raw_pages_semester{n}.json
  (skip OCR entirely, go straight to 02_chunk_text.py)

DPI: 200 (recommended balance of quality vs. file size)
"""
import fitz  # PyMuPDF
import json
import re
from pathlib import Path

PDF_FILES = {
    1: "data/raw/grade8_semester1.pdf",
    2: "data/raw/grade8_semester2.pdf",
}
DPI = 200


def check_is_native_pdf(pdf_path: str) -> bool:
    """Sample 3 pages; if average char count > 100, it's a native (text) PDF."""
    doc = fitz.open(pdf_path)
    sample_pages = [4, 9, 14]
    total_chars = sum(
        len(doc[p].get_text("text").strip())
        for p in sample_pages if p < len(doc)
    )
    doc.close()
    return (total_chars // len(sample_pages)) > 100


def extract_native_pdf(pdf_path: str, semester: int) -> list[dict]:
    """Extract text directly from a native PDF (no OCR needed)."""
    doc = fitz.open(pdf_path)
    pages = []
    current_unit = "Unit 1"
    print(f"  Extracting text directly from native PDF ({len(doc)} pages)...")

    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text").strip()
        if len(text) < 30:
            continue

        unit_match = re.search(r'Unit\s+(10|[1-9])\b', text, re.IGNORECASE)
        if unit_match:
            current_unit = f"Unit {unit_match.group(1)}"

        section = "General"
        for pattern, name in [
            (r'Section\s+A', "Section A"),
            (r'Section\s+B', "Section B"),
            (r'Grammar\s+Focus', "Grammar Focus"),
            (r'Self\s+Check', "Self Check"),
        ]:
            if re.search(pattern, text, re.IGNORECASE):
                section = name
                break

        pages.append({
            "page_num": page_num + 1,
            "text": text,
            "unit": current_unit,
            "section": section,
            "semester": semester,
            "ocr_method": "native_pymupdf",
            "char_count": len(text),
        })

    doc.close()
    return pages


def pdf_to_images(semester: int) -> list[str]:
    """Convert a scanned PDF to PNG images. Returns list of image paths."""
    pdf_path = PDF_FILES[semester]
    if not Path(pdf_path).exists():
        print(f"  ⚠️  Not found: {pdf_path}")
        return []

    size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
    print(f"  File: {pdf_path} ({size_mb:.1f} MB)")
    print(f"  Detecting PDF type...")

    if check_is_native_pdf(pdf_path):
        print(f"  ✅ Native PDF — extracting text directly (no OCR needed)")
        pages = extract_native_pdf(pdf_path, semester)
        if pages:
            Path("data/processed").mkdir(parents=True, exist_ok=True)
            output_path = f"data/processed/raw_pages_semester{semester}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(pages, f, ensure_ascii=False, indent=2)
            char_avg = sum(p["char_count"] for p in pages) // len(pages)
            print(f"  ✅ {len(pages)} pages → {output_path} (avg {char_avg} chars/page)")
            print(f"  ⏭️  Skip OCR steps — proceed directly to:")
            print(f"       python scripts/02_chunk_text.py")
        return []  # no images generated

    # --- Scanned PDF: convert to PNG ---
    print(f"  📷 Scanned PDF — converting to PNG at {DPI} DPI...")
    output_dir = Path(f"data/images/semester{semester}")
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    image_paths = []
    matrix = fitz.Matrix(DPI / 72, DPI / 72)

    for page_num in range(total_pages):
        pixmap = doc[page_num].get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        out_path = output_dir / f"page_{page_num + 1:03d}.png"
        pixmap.save(str(out_path))
        image_paths.append(str(out_path))
        if (page_num + 1) % 20 == 0 or (page_num + 1) == total_pages:
            print(f"    {page_num + 1}/{total_pages} pages converted")

    doc.close()

    manifest = {
        "semester": semester,
        "total_pages": total_pages,
        "dpi": DPI,
        "image_paths": image_paths,
        "needs_ocr": True,
    }
    manifest_path = f"data/images/semester{semester}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    size_out = sum(Path(p).stat().st_size for p in image_paths) / (1024 * 1024)
    print(f"  ✅ {total_pages} pages → {output_dir}/ ({size_out:.0f} MB total)")
    print(f"  📋 Manifest → {manifest_path}")
    return image_paths


def main():
    print("=" * 50)
    print("Step 0a: PDF → Images")
    print("=" * 50)

    Path("data/images").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    results = {}
    for semester in [1, 2]:
        print(f"\n--- Semester {semester} ---")
        if not Path(PDF_FILES[semester]).exists():
            print(f"  File not found, skipping.")
            continue
        images = pdf_to_images(semester)
        results[semester] = len(images)

    print("\n" + "=" * 50)
    print("Summary:")
    for semester, count in results.items():
        if count > 0:
            print(f"  Semester {semester}: {count} images → run OCR next")
            print(f"    → python scripts/00b_ocr_with_minimax.py")
        else:
            print(f"  Semester {semester}: native PDF, text extracted directly")
            print(f"    → python scripts/02_chunk_text.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
