"""Curated common-word list for search ranking boost (P4)."""

from __future__ import annotations

from pathlib import Path
from typing import Set

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CURATED_PATH = ROOT / "data" / "lexicon" / "curated_common.txt"

_curated: Set[str] = set()
_loaded = False


def load_curated_common(path: Path | str = DEFAULT_CURATED_PATH) -> int:
    global _curated, _loaded

    curated_path = Path(path)
    words: Set[str] = set()
    count = 0

    if curated_path.is_file():
        with open(curated_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                words.add(line)
                count += 1

    _curated = words
    _loaded = True
    return count


def ensure_curated_loaded(path: Path | str | None = None) -> None:
    if _loaded:
        return
    load_curated_common(path or DEFAULT_CURATED_PATH)


def is_curated_common(char: str) -> bool:
    if not char or not char.strip():
        return False
    ensure_curated_loaded()
    return char.strip() in _curated


def curated_sort_boost(char: str) -> int:
    """1 if curated (sorts earlier when negated in tuple), else 0."""
    return 1 if is_curated_common(char) else 0


def reset_curated_for_tests() -> None:
    global _curated, _loaded
    _curated = set()
    _loaded = False
