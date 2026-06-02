"""
Step 05: Extract vocabulary from OCR'd / native-extracted textbook content.

Strategy:
  - For each semester, scan raw_pages JSON pages
  - When section is "Vocabulary" or page text contains vocabulary list patterns,
    extract word / phonetic / translation triples
  - Group by unit, output to data/vocab/vocab_semester{n}.json
  - Idempotent: skips if output exists (use --force to overwrite)
"""
import argparse
import json
import re
from pathlib import Path

# Match: word /phonetic/ translation
#   e.g. "game /ɡeɪm/ n. 游戏；运动 p.3"
#   or   "look /lʊk/ v. 看；注视"
WORD_PATTERN = re.compile(
    r'^([a-zA-Z][a-zA-Z\-\s]*?)\s+'
    r'/?\s*'
    r'((?:/[^/]+/)?)\s*'
    r'(?:(n|v|adj|adv|prep|conj|pron|interj|num|art|aux)\.\s*)?'
    r'([^p\d\n]+?)'
    r'(?:\s+p\.\d+|\s*p\.\d+|\s+[a-z]\.\s*\d+)*\s*$',
    re.MULTILINE,
)


def extract_words_from_text(text: str) -> list[dict]:
    """Find word/phonetic/translation lines in text."""
    words: list[dict] = []
    seen: set[str] = set()

    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 5 or len(line) > 150:
            continue
        # Must contain phonetic markers (slashes around something)
        if "/" not in line:
            continue
        # Must have at least one Chinese character (translation)
        if not re.search(r'[一-鿿]', line):
            continue

        # Try to split: word phonetic translation
        m = re.match(
            r'^([a-zA-Z][a-zA-Z\-\s\']{1,30}?)\s+'
            r'(/?/?[^/]+?/[^/]+/?/?)\s+'
            r'(.*)$',
            line,
        )
        if not m:
            continue
        word, phonetic, rest = m.groups()
        word = word.strip()
        phonetic = phonetic.strip()

        # Extract POS + translation from rest
        pos_m = re.match(r'((?:n|v|adj|adv|prep|conj|pron|interj|num|art|aux|vi|vt)\.)\s*(.+)', rest)
        if pos_m:
            pos, translation = pos_m.group(1), pos_m.group(2).strip()
        else:
            pos = ""
            translation = rest.strip()
        # Clean trailing page refs
        translation = re.sub(r'\s*p\.\d+', '', translation).strip()

        if len(word) < 2 or len(translation) < 1:
            continue
        if word.lower() in seen:
            continue
        seen.add(word.lower())
        words.append({
            "word": word,
            "phonetic": phonetic,
            "pos": pos,
            "translation": translation,
        })

    return words


def extract_semester(semester: int) -> dict:
    pages_path = Path(f"data/processed/raw_pages_semester{semester}.json")
    if not pages_path.exists():
        return {"semester": semester, "words": []}

    with open(pages_path, encoding="utf-8") as f:
        pages = json.load(f)

    # Group words by unit
    unit_words: dict[str, list[dict]] = {}
    current_unit = "Unit 1"

    for page in pages:
        if page.get("unit"):
            current_unit = page["unit"]
        # Filter: only vocabulary pages
        section = page.get("section", "")
        if "Vocabulary" not in section and "vocab" not in page.get("text", "").lower()[:200]:
            continue

        words = extract_words_from_text(page["text"])
        if not words:
            continue
        unit_words.setdefault(current_unit, []).extend(words)

    # Deduplicate per unit, keep first occurrence
    all_words = []
    for unit, ws in unit_words.items():
        seen = set()
        unique = []
        for w in ws:
            if w["word"].lower() in seen:
                continue
            seen.add(w["word"].lower())
            w["unit"] = unit
            unique.append(w)
        all_words.extend(unique)

    return {"semester": semester, "total": len(all_words), "words": all_words}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    print("=" * 50)
    print("Step 05: Extract Vocabulary")
    print("=" * 50)

    Path("data/vocab").mkdir(parents=True, exist_ok=True)

    for semester in [1, 2]:
        out = Path(f"data/vocab/vocab_semester{semester}.json")
        if out.exists() and not args.force:
            print(f"  Semester {semester}: exists, skipping (use --force).")
            continue

        result = extract_semester(semester)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Stats
        unit_counts: dict[str, int] = {}
        for w in result["words"]:
            u = w.get("unit", "Unknown")
            unit_counts[u] = unit_counts.get(u, 0) + 1
        print(f"  Semester {semester}: {result['total']} words → {out}")
        for u in sorted(unit_counts, key=lambda x: (
                int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999, x)):
            print(f"    {u}: {unit_counts[u]} words")


if __name__ == "__main__":
    main()
