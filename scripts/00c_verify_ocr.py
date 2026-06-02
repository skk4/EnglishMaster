"""
Step 0c: OCR Quality Verification

Checks both semesters in data/processed/raw_pages_semester{n}.json.
Pass criteria:
  - Average chars per page >= 150
  - Pages with English content >= 60%
  - Low-quality pages (< 100 chars) < 20%
  - No obviously wrong unit labels (e.g. "Unit 125")

Prints a random sample of 8 pages for manual review.
"""
import json
import random
import re
from pathlib import Path

PASS_AVG_CHARS   = 150   # minimum average chars/page
PASS_EN_PCT      = 60    # minimum % of pages containing English words
PASS_LOW_QTY_PCT = 20    # maximum % of pages below 100 chars
MAX_VALID_UNIT   = 20    # unit numbers above this are likely mis-detections


def verify_semester(semester: int, sample_size: int = 8) -> bool:
    path = Path(f"data/processed/raw_pages_semester{semester}.json")
    if not path.exists():
        print(f"  ❌ Not found: {path}")
        return False

    with open(path, encoding="utf-8") as f:
        pages = json.load(f)

    print(f"\n{'='*55}")
    print(f"OCR Quality Check — Semester {semester}")
    print(f"{'='*55}")
    print(f"Total pages : {len(pages)}")

    # --- Char count stats ---
    char_counts = [p.get("char_count", len(p["text"])) for p in pages]
    avg   = sum(char_counts) // len(char_counts)
    low_q = sum(1 for c in char_counts if c < 100)
    low_q_pct = 100 * low_q // len(char_counts)

    print(f"\n[Char count]")
    print(f"  min={min(char_counts)}  max={max(char_counts)}  avg={avg}")
    flag = "⚠️ " if avg < PASS_AVG_CHARS else "✅"
    print(f"  {flag} avg chars/page: {avg}  (threshold >= {PASS_AVG_CHARS})")
    flag = "⚠️ " if low_q_pct >= PASS_LOW_QTY_PCT else "✅"
    print(f"  {flag} pages < 100 chars: {low_q} ({low_q_pct}%)  (threshold < {PASS_LOW_QTY_PCT}%)")

    # --- English coverage ---
    has_en = sum(1 for p in pages if re.search(r'[A-Za-z]{3,}', p["text"]))
    en_pct = 100 * has_en // len(pages)
    flag = "⚠️ " if en_pct < PASS_EN_PCT else "✅"
    print(f"\n[English coverage]")
    print(f"  {flag} Pages with English: {has_en}/{len(pages)} ({en_pct}%)  (threshold >= {PASS_EN_PCT}%)")

    # --- OCR method ---
    methods: dict[str, int] = {}
    for p in pages:
        m = p.get("ocr_method", "unknown")
        methods[m] = methods.get(m, 0) + 1
    print(f"\n[OCR method]")
    for m, count in methods.items():
        print(f"  {m}: {count} pages")

    # --- Unit distribution ---
    unit_counts: dict[str, int] = {}
    bad_units: list[str] = []
    for p in pages:
        u = p.get("unit", "Unknown")
        unit_counts[u] = unit_counts.get(u, 0) + 1
        # detect mis-labelled unit numbers
        m = re.search(r'Unit\s+(\d+)', u)
        if m and int(m.group(1)) > MAX_VALID_UNIT:
            if u not in bad_units:
                bad_units.append(u)

    print(f"\n[Unit distribution]")
    for u in sorted(unit_counts, key=lambda x: (
            int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999, x)):
        flag = " ⚠️ (suspicious unit number)" if u in bad_units else ""
        print(f"  {u}: {unit_counts[u]} pages{flag}")

    # --- Random sample for manual review ---
    print(f"\n[Random sample — {sample_size} pages]")
    sample = sorted(random.sample(pages, min(sample_size, len(pages))),
                    key=lambda x: x["page_num"])
    for p in sample:
        preview = p["text"][:200].replace("\n", " | ")
        print(f"\n  Page {p['page_num']:3d} | {p['unit']} / {p['section']} | {p['char_count']} chars")
        print(f"  {preview}")

    # --- Pass / Fail ---
    issues = []
    if avg < PASS_AVG_CHARS:
        issues.append(f"avg chars too low ({avg} < {PASS_AVG_CHARS}) — consider DPI=300 in 00a")
    if en_pct < PASS_EN_PCT:
        issues.append(f"English coverage too low ({en_pct}% < {PASS_EN_PCT}%)")
    if low_q_pct >= PASS_LOW_QTY_PCT:
        issues.append(f"too many low-quality pages ({low_q_pct}% >= {PASS_LOW_QTY_PCT}%)")
    if bad_units:
        issues.append(f"suspicious unit labels detected: {bad_units} — likely page-number mis-detection, safe to ignore for RAG")

    print(f"\n{'='*55}")
    if not issues:
        print(f"✅ Semester {semester}: ALL CHECKS PASSED")
    else:
        print(f"⚠️  Semester {semester}: issues found (review before proceeding):")
        for issue in issues:
            print(f"   - {issue}")
    print(f"{'='*55}")

    # bad_units is a soft warning, not a hard fail
    hard_issues = [i for i in issues if "suspicious unit" not in i]
    return len(hard_issues) == 0


def main():
    print("=" * 55)
    print("Step 0c: OCR Quality Verification")
    print("=" * 55)

    found = False
    all_passed = True

    for semester in [1, 2]:
        path = Path(f"data/processed/raw_pages_semester{semester}.json")
        if path.exists():
            found = True
            passed = verify_semester(semester)
            all_passed = all_passed and passed

    if not found:
        print("❌ No processed files found. Run 00a and 00b first.")
        return

    print()
    if all_passed:
        print("🎉 All hard checks passed!")
        print("   Next: python scripts/02_chunk_text.py")
    else:
        print("🔧 Fix hard issues above, or manually confirm quality is acceptable.")
        print("   Suspicious unit labels (e.g. Unit 125) are soft warnings — safe to proceed.")


if __name__ == "__main__":
    main()
