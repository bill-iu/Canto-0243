"""Essay-cantonese corpus frequency index (sort signal only, no injection)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ESSAY_PATH = ROOT / "data" / "essay" / "essay-cantonese.txt"

_freq_by_char: Dict[str, int] = {}
_loaded = False


def load_essay_corpus(path: Path | str = DEFAULT_ESSAY_PATH) -> int:
    """Load ``詞<TAB>頻次`` lines. Returns row count."""
    global _freq_by_char, _loaded

    corpus_path = Path(path)
    index: Dict[str, int] = {}
    count = 0

    if not corpus_path.is_file():
        _freq_by_char = index
        _loaded = True
        return 0

    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            word = parts[0].strip()
            try:
                freq = int(parts[1].strip())
            except ValueError:
                continue
            if not word or freq < 0:
                continue
            index[word] = freq
            count += 1

    _freq_by_char = index
    _loaded = True
    return count


def ensure_essay_loaded(path: Optional[Path | str] = None) -> None:
    if _loaded:
        return
    load_essay_corpus(path or DEFAULT_ESSAY_PATH)


def get_essay_frequency(char: str) -> int:
    """Higher = more common in essay corpus. Missing words -> 0."""
    if not char or not char.strip():
        return 0
    ensure_essay_loaded()
    return int(_freq_by_char.get(char.strip(), 0))


def reset_essay_for_tests() -> None:
    global _freq_by_char, _loaded
    _freq_by_char = {}
    _loaded = False
