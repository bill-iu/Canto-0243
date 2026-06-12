"""Equals-query handler (legacy framed equals syntax).

Left ``=`` anchors initial; right ``=`` anchors final; whole-word templates like ``香港=``.
Not part of PositionMatchEngine — phoneme sandwich / exact-match logic stays here.

Product rules: see CONTEXT.md §「等號查詢」.
參考字只提供聲母或韻母錨（非整段讀音）；逐格 code digit 單獨約束聲調（鬆/緊見 mode）。
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from app.models.word import Word
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_ensure_service import ensure_word_in_db
from app.services.word_serializer import (
    deduplicate_words,
    get_word_text,
    serialize_page,
)
from app.utils.json_helpers import load_json_list


class EqualsQueryHandler:
    """Execute legacy ``=``-framed queries (e.g. ``2=我3``, ``香港=``)."""

    def execute(
        self,
        q: str,
        code: Optional[str],
        mode: str,
        limit: int,
        offset: int,
        db,
    ) -> List[dict]:
        match = re.match(r"^(\d*)(=)?([一-龥]+)?(=)?(\d*)$", q)
        if not match:
            return []

        left_code = match.group(1) or ""
        target_str = match.group(3) or ""
        right_code = match.group(5) or ""
        right_equal = bool(match.group(4))

        full_code = left_code + right_code

        if not target_str:
            return []

        target_rows = db.query(Word).filter(Word.char == target_str).all()
        if not target_rows:
            target_rows = ensure_word_in_db(db, target_str)
        target = target_rows[0] if target_rows else None
        if not target:
            return []

        target_initials = load_json_list(target.initials)
        target_finals = load_json_list(target.finals)

        target_length = len(target_str)
        expected_length = len(left_code) + len(right_code) or target_length

        query = db.query(Word)
        query = apply_code_filter(query, full_code, mode)
        query = query.filter(length_filter(expected_length))
        is_rhyme_match = right_equal
        # 錨字對齊左碼尾位：2=我3 → pos 0；23=你4 → pos 1（code 3 那格同聲「你」）。
        start_pos = max(0, len(left_code) - target_length)

        if start_pos == 0 and target_length == expected_length:
            target_parts = target_finals if is_rhyme_match else target_initials
            target_json = json.dumps(target_parts)
            compare_field = Word.finals if is_rhyme_match else Word.initials
            query = query.filter(compare_field == target_json)

            results = query.order_by(Word.char).offset(offset).limit(limit).all()
            return serialize_page(deduplicate_words(results), offset, limit)

        candidates = query.order_by(Word.char).limit(2000).all()
        filtered = []
        target_parts = target_finals if is_rhyme_match else target_initials
        # Code 夾住錨點（2=我3 / 2我=3）：「我」為聲母/韻母錨，不要求結果含字面錨字。
        phoneme_anchor_only = bool(left_code and right_code)
        for word in candidates:
            char_text = get_word_text(word)
            if not phoneme_anchor_only and target_str and target_str not in char_text:
                continue
            word_parts = load_json_list(word.finals if is_rhyme_match else word.initials)
            if not word_parts:
                continue
            match_ok = True
            for i in range(target_length):
                pos = start_pos + i
                if pos < len(word_parts) and i < len(target_parts):
                    if target_parts[i] and target_parts[i] != word_parts[pos]:
                        match_ok = False
                        break
            if match_ok:
                filtered.append(word)

        return serialize_page(deduplicate_words(filtered), offset, limit)


def handle_equals_syntax(
    q: str,
    code: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    db,
) -> List[dict]:
    """Thin wrapper for QueryEngine registry."""
    return EqualsQueryHandler().execute(q, code, mode, limit, offset, db)
