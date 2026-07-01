"""Lexicon ingest from SSOT raw files."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.lexicon.candidates import LexiconCandidate
from app.utils.jyutping_codec import get_0243_code
from ingest.syn_ant_manifest import resolve_source_path

_SOURCE_RIME = "rime"
_CJK = re.compile(r"[\u4e00-\u9fff]")


def ingest_rime_char_csv(path: Path | str) -> list[LexiconCandidate]:
    csv_path = Path(path)
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    if not csv_path.is_file():
        return out
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            char = str(row.get("char") or "").strip()
            jyutping = str(row.get("jyutping") or "").strip()
            if not char or not jyutping or not _CJK.search(char) or len(char) != 1:
                continue
            code = get_0243_code(jyutping) or ""
            if not code:
                continue
            key = (char, jyutping)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                LexiconCandidate(char=char, jyutping=jyutping, code=code, sources=(_SOURCE_RIME,))
            )
    return out


def ingest_lexicon_json(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    json_path = Path(path)
    if not json_path.is_file():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        char = str(item.get("char") or "").strip()
        jyutping = str(item.get("jyutping") or "").strip()
        code = str(item.get("code") or "").strip() or (get_0243_code(jyutping) or "")
        if not char or not jyutping or not code or not _CJK.search(char):
            continue
        key = (char, jyutping)
        if key in seen:
            continue
        seen.add(key)
        out.append(LexiconCandidate(char=char, jyutping=jyutping, code=code, sources=(source_id,)))
    return out


def ingest_source(src: Dict[str, Any]) -> list[LexiconCandidate]:
    parser = str(src.get("parser") or "")
    source_id = str(src.get("id") or "")
    if parser == "rime_char":
        path = resolve_source_path(src) or Path("")
        return ingest_rime_char_csv(path)
    if parser == "lexicon_json":
        path = resolve_source_path(src) or Path("")
        return ingest_lexicon_json(path, source_id=source_id)
    return []
