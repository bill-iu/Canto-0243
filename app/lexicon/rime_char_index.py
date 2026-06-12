"""Rime cantonese-upstream char.csv index (single-char pron_rank=預設)."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

from app.lexicon.static_index import LexiconEntry
from app.utils.jyutping_codec import get_0243_code

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHAR_CSV = ROOT / "data" / "rime" / "char.csv"
DEFAULT_PRON_RANK = "預設"

PRON_RANK_SORT = {"預設": 0, "常用": 1, "罕見": 2}
UNKNOWN_PRON_RANK_SORT = 99

_entries_by_char: Dict[str, List[LexiconEntry]] = {}
_rank_by_char_jyut: Dict[tuple[str, str], int] = {}
_loaded = False


def _is_canto_char(text: str) -> bool:
    return bool(text and re.search(r"[\u4e00-\u9fff]", text))


def load_rime_char_csv(path: Path | str = DEFAULT_CHAR_CSV) -> int:
    """Load char.csv: 預設 rows -> ensure entries; all ranks -> pron_rank_sort lookup."""
    global _entries_by_char, _rank_by_char_jyut, _loaded

    csv_path = Path(path)
    index: Dict[str, List[LexiconEntry]] = {}
    rank_map: Dict[tuple[str, str], int] = {}
    count = 0

    if not csv_path.is_file():
        _entries_by_char = index
        _rank_by_char_jyut = rank_map
        _loaded = True
        return 0

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            char = str(row.get("char") or "").strip()
            jyutping = str(row.get("jyutping") or "").strip()
            pron_rank = str(row.get("pron_rank") or "").strip()
            if not char or not _is_canto_char(char) or len(char) != 1:
                continue
            if not jyutping:
                continue
            rank_val = PRON_RANK_SORT.get(pron_rank, UNKNOWN_PRON_RANK_SORT)
            rank_map[(char, jyutping)] = rank_val
            if pron_rank != DEFAULT_PRON_RANK:
                continue
            code = get_0243_code(jyutping) or ""
            if not code:
                continue
            entry = LexiconEntry(char=char, jyutping=jyutping, code=code)
            bucket = index.setdefault(char, [])
            if not any(e.jyutping == jyutping and e.code == code for e in bucket):
                bucket.append(entry)
                count += 1

    _entries_by_char = index
    _rank_by_char_jyut = rank_map
    _loaded = True
    return count


def ensure_rime_char_loaded(path: Optional[Path | str] = None) -> None:
    if _loaded:
        return
    load_rime_char_csv(path or DEFAULT_CHAR_CSV)


def get_rime_char_entries(char: str) -> List[LexiconEntry]:
    if not char or len(char.strip()) != 1:
        return []
    ensure_rime_char_loaded()
    return list(_entries_by_char.get(char.strip(), []))


def pron_rank_sort_value(char: str, jyutping: str) -> int:
    """Lower = higher priority (預設=0, 常用=1, 罕見=2, unknown=99)."""
    if not char or not jyutping:
        return UNKNOWN_PRON_RANK_SORT
    ensure_rime_char_loaded()
    return _rank_by_char_jyut.get((char.strip(), jyutping.strip()), UNKNOWN_PRON_RANK_SORT)


def pron_rank_sort_value_for_word(char: str, jyutping: str) -> int:
    """Word-level: max per-syllable rank (all 預設 beats mixed)."""
    text = (char or "").strip()
    jyut = (jyutping or "").strip()
    if not text or not jyut:
        return UNKNOWN_PRON_RANK_SORT
    syllables = jyut.split()
    if len(text) == 1:
        return pron_rank_sort_value(text, jyut)
    if len(text) != len(syllables):
        return UNKNOWN_PRON_RANK_SORT
    return max(pron_rank_sort_value(text[i], syllables[i]) for i in range(len(text)))


def reset_rime_char_for_tests() -> None:
    global _entries_by_char, _rank_by_char_jyut, _loaded
    _entries_by_char = {}
    _rank_by_char_jyut = {}
    _loaded = False
