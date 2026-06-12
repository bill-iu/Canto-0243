"""Load word-level entries from ingest JSON (data/raw/clean/*.json)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CLEAN_DIR = ROOT / "data" / "raw" / "clean"

_entries_by_char: Dict[str, List["LexiconEntry"]] = {}
_loaded = False


@dataclass(frozen=True)
class LexiconEntry:
    char: str
    jyutping: str
    code: str


def _is_canto_char(text: str) -> bool:
    return bool(text and re.search(r"[\u4e00-\u9fff]", text))


def load_lexicon_from_folder(folder: Path | str = DEFAULT_CLEAN_DIR) -> int:
    """Load ``{char, jyutping, code}`` rows from clean JSON files. Returns entry count."""
    global _entries_by_char, _loaded

    folder_path = Path(folder)
    index: Dict[str, List[LexiconEntry]] = {}
    count = 0

    if not folder_path.is_dir():
        _entries_by_char = index
        _loaded = True
        return 0

    for json_path in sorted(folder_path.glob("*.json")):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            char = str(item.get("char") or "").strip()
            jyutping = str(item.get("jyutping") or "").strip()
            code = str(item.get("code") or "").strip()
            if not char or not _is_canto_char(char) or not jyutping or not code:
                continue
            entry = LexiconEntry(char=char, jyutping=jyutping, code=code)
            bucket = index.setdefault(char, [])
            if not any(e.code == code and e.jyutping == jyutping for e in bucket):
                bucket.append(entry)
                count += 1

    _entries_by_char = index
    _loaded = True
    return count


def ensure_lexicon_loaded(folder: Optional[Path | str] = None) -> None:
    if _loaded:
        return
    load_lexicon_from_folder(folder or DEFAULT_CLEAN_DIR)


def get_lexicon_entries(char: str) -> List[LexiconEntry]:
    """Return all word-level ``(char, jyutping, code)`` rows for *char*."""
    if not char or not char.strip():
        return []
    ensure_lexicon_loaded()
    return list(_entries_by_char.get(char.strip(), []))


def reset_lexicon_for_tests() -> None:
    """Clear in-memory index (tests only)."""
    global _entries_by_char, _loaded
    _entries_by_char = {}
    _loaded = False
