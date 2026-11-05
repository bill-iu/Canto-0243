"""Rime cantonese-upstream char.csv index (single-char pron_rank=預設)."""

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from app.lexicon.static_index import LexiconEntry
from app.utils.han import contains_han
from app.utils.jyutping_codec import get_0243_code

from app.payload_root import get_payload_root

DEFAULT_PRON_RANK = "預設"


def _default_char_csv() -> Path:
    return get_payload_root() / "data" / "rime" / "char.csv"


def __getattr__(name: str):
    if name == "DEFAULT_CHAR_CSV":
        return _default_char_csv()
    if name == "ROOT":
        return get_payload_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

PRON_RANK_SORT = {"預設": 0, "常用": 1, "罕見": 2, "棄用": 3}
UNKNOWN_PRON_RANK_SORT = 99
# 錨點選項 union 剔除（ADR-0051 §3）；未知仍入選
ANCHOR_EXCLUDED_PRON_RANK_SORT = frozenset({PRON_RANK_SORT["罕見"], PRON_RANK_SORT["棄用"]})

_entries_by_char: Dict[str, List[LexiconEntry]] = {}
_rank_by_char_jyut: Dict[tuple[str, str], int] = {}
_loaded = False
_word_ranks_path: Path | None = None


@lru_cache(maxsize=4)
def load_word_pron_ranks(path: Path) -> dict[tuple[str, str], int]:
    """Explicit curated word grades; absent legacy payloads keep char fallback."""
    if not path.is_file():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"{path}: reading ranks must be a list")
    out: dict[tuple[str, str], int] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: invalid reading rank row")
        char = row.get("char")
        actual = row.get("ingested_char", char)
        jyutping = row.get("jyutping")
        if not all(isinstance(value, str) for value in (char, actual, jyutping)):
            raise ValueError(f"{path}: invalid reading rank strings")
        char, actual, jyutping = char.strip(), actual.strip(), " ".join(jyutping.split())
        label = row.get("pron_rank")
        if (not isinstance(label, str) or label not in PRON_RANK_SORT or len(char) < 2 or len(actual) != len(char)
                or len(char) != len(jyutping.split())
                or not re.fullmatch(r"[a-z]+[1-6](?: [a-z]+[1-6])*", jyutping)):
            raise ValueError(f"{path}: invalid reading rank for {char!r}")
        for literal in (char, actual):
            key = (literal, jyutping)
            value = PRON_RANK_SORT[label]
            if key in out and out[key] != value:
                raise ValueError(f"{path}: conflicting reading rank for {key!r}")
            out[key] = value
    return out


def _is_canto_char(text: str) -> bool:
    return contains_han(text)


def load_rime_char_csv(path: Path | str | None = None) -> int:
    """Load char.csv: 預設 rows -> ensure entries; all ranks -> pron_rank_sort lookup."""
    global _entries_by_char, _rank_by_char_jyut, _loaded, _word_ranks_path

    csv_path = Path(path) if path is not None else _default_char_csv()
    _word_ranks_path = csv_path.parent.parent / "lexicon" / "curated_reading_ranks.json"
    index: Dict[str, List[LexiconEntry]] = {}
    rank_map: Dict[tuple[str, str], int] = {}
    count = 0

    if not csv_path.is_file():
        _entries_by_char = index
        _rank_by_char_jyut = rank_map
        _loaded = True
        return 0

    rows_by_char: Dict[str, List[tuple[int, str, str, str]]] = {}
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
            code = get_0243_code(jyutping) or ""
            if not code:
                continue
            rows_by_char.setdefault(char, []).append((rank_val, pron_rank, jyutping, code))

    for char, ranked_rows in rows_by_char.items():
        preset = [r for r in ranked_rows if r[1] == DEFAULT_PRON_RANK]
        pick_from = preset if preset else [r for r in ranked_rows if r[0] == min(x[0] for x in ranked_rows)]
        bucket = index.setdefault(char, [])
        for _rank_val, _pron_rank, jyutping, code in pick_from:
            entry = LexiconEntry(char=char, jyutping=jyutping, code=code)
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
    load_rime_char_csv(path if path is not None else _default_char_csv())


def get_rime_char_entries(char: str) -> List[LexiconEntry]:
    if not char or len(char.strip()) != 1:
        return []
    ensure_rime_char_loaded()
    return list(_entries_by_char.get(char.strip(), []))


def pron_rank_sort_value(char: str, jyutping: str) -> int:
    """Lower = higher priority (預設=0, 常用=1, 罕見=2, 棄用=3, unknown=99)."""
    if not char or not jyutping:
        return UNKNOWN_PRON_RANK_SORT
    ensure_rime_char_loaded()
    return _rank_by_char_jyut.get((char.strip(), jyutping.strip()), UNKNOWN_PRON_RANK_SORT)


def pron_rank_sort_value_for_word(char: str, jyutping: str) -> int:
    """Explicit whole-word grade, otherwise max per-syllable Rime grade."""
    text = (char or "").strip()
    jyut = (jyutping or "").strip()
    if not text or not jyut:
        return UNKNOWN_PRON_RANK_SORT
    syllables = jyut.split()
    if len(text) == 1:
        return pron_rank_sort_value(text, jyut)
    if len(text) != len(syllables):
        return UNKNOWN_PRON_RANK_SORT
    ensure_rime_char_loaded()
    if _word_ranks_path is not None:
        value = load_word_pron_ranks(_word_ranks_path).get((text, " ".join(syllables)))
        if value is not None:
            return value
    return max(pron_rank_sort_value(text[i], syllables[i]) for i in range(len(text)))


def reset_rime_char_for_tests() -> None:
    global _entries_by_char, _rank_by_char_jyut, _loaded, _word_ranks_path
    _entries_by_char = {}
    _rank_by_char_jyut = {}
    _loaded = False
    _word_ranks_path = None
    load_word_pron_ranks.cache_clear()
