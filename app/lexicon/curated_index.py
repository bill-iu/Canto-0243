"""Curated common-word list for search ranking boost (P4)."""

from __future__ import annotations

from pathlib import Path
from typing import Set

from app.payload_root import get_payload_root


def _default_path() -> Path:
    return get_payload_root() / "data" / "lexicon" / "curated_common.txt"


def __getattr__(name: str):
    if name == "DEFAULT_CURATED_PATH":
        return _default_path()
    if name == "ROOT":
        return get_payload_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

_curated: Set[str] = set()
_loaded = False


def load_curated_common(path: Path | str | None = None) -> int:
    global _curated, _loaded

    curated_path = Path(path) if path is not None else _default_path()
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
    load_curated_common(path)


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
