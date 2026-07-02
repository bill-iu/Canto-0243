"""Lexicon ingest from SSOT raw files."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.lexicon.candidates import LexiconCandidate
from app.utils.jyutping_codec import get_0243_code
from ingest.lexicon_validate import is_valid_word_lexicon_reading
from ingest.lexicon_raw_paths import resolve_lexicon_raw_path
from ingest.syn_ant_manifest import resolve_source_path

_SOURCE_RIME = "rime"
_CJK = re.compile(r"[\u4e00-\u9fff]")
_JYUTPING_TOKEN = re.compile(r"^[a-z]+\d$", re.IGNORECASE)


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
        if len(char) >= 2 and not is_valid_word_lexicon_reading(char, jyutping):
            continue
        key = (char, jyutping)
        if key in seen:
            continue
        seen.add(key)
        out.append(LexiconCandidate(char=char, jyutping=jyutping, code=code, sources=(source_id,)))
    return out


def _append_candidate(
    out: list[LexiconCandidate],
    seen: set[tuple[str, str]],
    *,
    char: str,
    jyutping: str,
    source_id: str,
) -> None:
    code = get_0243_code(jyutping) or ""
    if not char or not jyutping or not code or not _CJK.search(char):
        return
    if len(char) >= 2 and not is_valid_word_lexicon_reading(char, jyutping):
        return
    key = (char, jyutping)
    if key in seen:
        return
    seen.add(key)
    out.append(LexiconCandidate(char=char, jyutping=jyutping, code=code, sources=(source_id,)))


def ingest_words_hk_wordslist(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    json_path = Path(path)
    if not json_path.is_file():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return ingest_lexicon_json(json_path, source_id=source_id)
    if not isinstance(data, dict):
        return []
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    for char, readings in data.items():
        literal = str(char or "").strip()
        if not literal:
            continue
        if not isinstance(readings, list):
            continue
        for raw_jy in readings:
            jyutping = str(raw_jy or "").strip()
            _append_candidate(out, seen, char=literal, jyutping=jyutping, source_id=source_id)
    return out


def _candidates_from_kaifang_array(arr: list, *, source_id: str) -> list[LexiconCandidate]:
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    i = 0
    while i < len(arr):
        char = str(arr[i] or "").strip()
        i += 1
        if not char or not _CJK.search(char):
            continue
        syllables: list[str] = []
        while len(syllables) < len(char) and i < len(arr):
            token = str(arr[i] or "").strip()
            if _JYUTPING_TOKEN.match(token):
                syllables.append(token)
                i += 1
            else:
                break
        if len(syllables) != len(char):
            continue
        jyutping = " ".join(syllables)
        if len(char) == 1 and i < len(arr):
            gloss = str(arr[i] or "").strip()
            if gloss and not _JYUTPING_TOKEN.match(gloss):
                i += 1
        _append_candidate(out, seen, char=char, jyutping=jyutping, source_id=source_id)
    return out


def ingest_kaifang_txt(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    txt_path = Path(path)
    if not txt_path.is_file():
        return []
    try:
        text = txt_path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            arr = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(arr, list):
            return _candidates_from_kaifang_array(arr, source_id=source_id)
    return []


def ingest_source(src: Dict[str, Any]) -> list[LexiconCandidate]:
    parser = str(src.get("parser") or "")
    source_id = str(src.get("id") or "")
    if parser == "rime_char":
        path = resolve_source_path(src) or Path("")
        return ingest_rime_char_csv(path)
    if parser == "words_hk_wordslist":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_words_hk_wordslist(path, source_id=source_id)
    if parser == "kaifang_txt":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_kaifang_txt(path, source_id=source_id)
    if parser == "lexicon_json":
        path = resolve_lexicon_raw_path(src) or resolve_source_path(src) or Path("")
        return ingest_lexicon_json(path, source_id=source_id)
    return []
