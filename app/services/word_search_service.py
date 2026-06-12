"""Legacy compound-ant handler (C3: migrate to PositionMatchEngine)."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.position_match import word_matches_last_final
from app.services.phoneme_lookup import final_options_for_char
from app.services.word_db_filters import length_filter
from app.services.word_serializer import serialize_page
from app.utils.jyutping_codec import get_code_variants


def handle_antonym_compound_syntax(
    parsed: dict,
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> List[dict]:
    from app.services.syn_ant_service import build_char_antonym_pairs

    ant_pairs = build_char_antonym_pairs(db)
    if not ant_pairs:
        return []

    candidates: set[str] = set()
    for a, b in ant_pairs:
        if len(a) == 1 and len(b) == 1:
            candidates.add(a + b)
            candidates.add(b + a)
    if not candidates:
        return []

    query = db.query(Word).filter(Word.char.in_(list(candidates)), length_filter(2))
    code_prefix = parsed.get("code_prefix")
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        query = query.filter(Word.code.in_(variants))

    last_final_options: Optional[set[str]] = None
    rhyme_char = parsed.get("rhyme_char")
    if rhyme_char:
        last_final_options = final_options_for_char(rhyme_char, db)
        if not last_final_options:
            return []

    results: List[Word] = []
    seen_chars: set[str] = set()
    for word in query.order_by(Word.char, Word.code, Word.jyutping).all():
        ch = word.char or ""
        if len(ch) != 2:
            continue
        if (ch[0], ch[1]) not in ant_pairs and (ch[1], ch[0]) not in ant_pairs:
            continue
        if not word_matches_last_final(word, last_final_options):
            continue
        if ch in seen_chars:
            continue
        seen_chars.add(ch)
        results.append(word)

    return serialize_page(results, offset, limit, result_type="word")


__all__ = ["handle_antonym_compound_syntax"]
