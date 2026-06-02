import json
import random
from pathlib import Path
from typing import Optional


def _load_vocab(semester: int) -> dict:
    path = Path(f"data/vocab/vocab_semester{semester}.json")
    if not path.exists():
        return {"semester": semester, "words": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_unit_vocab(semester: int, unit: str) -> list[dict]:
    """Return all words for a specific unit."""
    data = _load_vocab(semester)
    return [w for w in data.get("words", []) if w.get("unit") == unit]


def list_units(semester: int) -> list[str]:
    """List all units that have vocabulary."""
    data = _load_vocab(semester)
    units = sorted({
        w.get("unit", "Unknown")
        for w in data.get("words", [])
    }, key=lambda u: (
        int(''.join(c for c in u if c.isdigit()) or 999),
        u,
    ))
    return units


def get_practice_words(semester: int, n: int = 10, units: Optional[list[str]] = None) -> list[dict]:
    """Pick n random words, optionally restricted to specific units."""
    data = _load_vocab(semester)
    pool = data.get("words", [])
    if units:
        pool = [w for w in pool if w.get("unit") in units]
    return random.sample(pool, min(n, len(pool)))
