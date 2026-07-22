from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.domain.lexicon.phoneme_codec import decode_phoneme_field
from app.domain.lexicon.ranking import search_result_sort_key
from app.lexicon.essay_index import get_essay_frequency
from app.models.word import Word
from app.domain.relation_pool import project_relation_pool
from app.utils.jyutping_codec import split_jyutping_parts


SOURCE_FLAG_LABELS = (
    ("hsk30", 1),
    ("kaifang", 2),
    ("rime", 4),
    ("rime_phrase", 8),
    ("rime_words", 16),
    ("words_hk", 32),
)

TONE_TO_0243 = {1: "3", 2: "9", 3: "4", 4: "0", 5: "4", 6: "2"}


def _code0243_from_jyutping(jyutping: str) -> str:
    if not jyutping or not jyutping.strip():
        return ""
    out: list[str] = []
    for syl in jyutping.strip().split():
        tone = int(syl[-1]) if syl and syl[-1].isdigit() else None
        out.append(TONE_TO_0243.get(tone, "?") if tone else "?")
    return "".join(out)


def _parse_phoneme_list(raw: Any, dim: str) -> list[str]:
    """Display phonemes: compact (j2) → legacy JSON → empty."""
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str) and raw.strip():
        s = raw.strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                return [str(x) for x in parsed] if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return decode_phoneme_field(s, dim)  # type: ignore[arg-type]
    return []


def _decode_source_flags(flags: int | None) -> list[str]:
    n = int(flags or 0)
    if not n:
        return []
    return [label for label, bit in SOURCE_FLAG_LABELS if n & bit]


def build_entry_detail(db: Session, literal: str) -> dict[str, Any] | None:
    text = (literal or "").strip()
    if not text:
        return None
    rows = db.query(Word).filter(Word.char == text).all()
    if not rows:
        return None
    rows = sorted(rows, key=search_result_sort_key)

    pool = project_relation_pool(db, text)
    syns = [
        r["char"]
        for r in pool.syns
        if r.get("in_db") and r.get("char") and r["char"] != text
    ][:24]
    ants = [
        r["char"]
        for r in pool.ants
        if r.get("in_db") and r.get("char") and r["char"] != text
    ][:24]

    flag_union = 0
    readings = []
    for row in rows:
        flag_union |= int(row.source_flags or 0)
        jyut = row.jyutping or ""
        initials = _parse_phoneme_list(row.initials, "initial")
        finals = _parse_phoneme_list(row.finals, "final")
        # 生成／合成詞條常只有粵拼 → 由 jyutping 拆聲母／韻母
        if jyut and not any(initials) and not any(finals):
            initials, finals, _tones = split_jyutping_parts(jyut)
        readings.append(
            {
                "jyutping": jyut,
                "code0243": row.code or "",
                "code02493": _code0243_from_jyutping(jyut) or (row.code or ""),
                "initials": initials,
                "finals": finals,
            }
        )

    length = rows[0].length if rows[0].length is not None else len(text)
    return {
        "literal": text,
        "length": length,
        "corpusWeight": get_essay_frequency(text),
        "readings": readings,
        "sources": _decode_source_flags(flag_union),
        "syns": syns,
        "ants": ants,
    }