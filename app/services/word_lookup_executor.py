"""詞條 lookup executor：純數字、純字面、粵拼查詢與 WordLookup fallback。"""

from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.domain.lexicon.lookup_layout import build_lookup_layout
from app.domain.lexicon.ranking import search_result_sort_key, sort_search_results
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_ensure_service import ensure_word_in_db, warm_ref_char_for_lookup
from app.services.jyutping_match import expected_word_length, matches_jyutping_query
from app.services.word_serializer import (
    deduplicate_words,
    paginate,
    serialize_word,
)


class WordLookupExecutor:
    """Per-request executor for 詞條 lookup（非位置型、非近反義）。"""

    def __init__(self, db: Session):
        self._db = db

    def _sorted_pure_digit_words(self, q: str, mode: str) -> List[Word]:
        query = self._db.query(Word)
        query = apply_code_filter(query, q, mode)
        query = query.filter(length_filter(len(q)))
        words = deduplicate_words(query.all())
        words.sort(key=search_result_sort_key)
        return words

    def pure_digit(
        self,
        q: str,
        code: Optional[str],
        mode: str,
        limit: int,
        offset: int,
    ) -> tuple[List[dict], int]:
        words = self._sorted_pure_digit_words(q, mode)
        page = paginate(words, offset, limit)
        return [serialize_word(w) for w in page], len(words)

    def pure_canto(
        self,
        q: str,
        code: Optional[str],
        mode: str,
        limit: int,
        offset: int,
    ) -> List[dict]:
        raw_targets: List[Word] = []
        if re.search(r"[\u4e00-\u9fff]", q):
            raw_targets = ensure_word_in_db(self._db, q)
        if not raw_targets:
            raw_targets = self._db.query(Word).filter(Word.char == q).all()
        target_words = deduplicate_words(raw_targets)
        if target_words:
            if len(q) >= 1:
                warm_ref_char_for_lookup(q[-1], self._db)
            built = build_lookup_layout(q, raw_targets, self._db)
            return paginate(built, offset, limit)
        return []

    def jyut_fragment(self, q: str, limit: int, offset: int) -> List[dict]:
        word_len = expected_word_length(q)
        if word_len is None:
            return []

        query = self._db.query(Word).filter(length_filter(word_len))
        candidates = query.all()
        matched = [w for w in candidates if matches_jyutping_query(w.jyutping or "", q)]
        ordered = sort_search_results(matched)
        page = paginate(ordered, offset, limit)
        return [serialize_word(w) for w in page]

    def lookup(
        self,
        q: str,
        code: Optional[str],
        mode: str,
        limit: int,
        offset: int,
    ) -> List[dict]:
        """WordLookupQuery path：canto 優先，含字母則 fallback jyut。"""
        res = self.pure_canto(q, code, mode, limit, offset)
        if res:
            return res
        if re.search(r"[a-zA-Z]", q):
            return self.jyut_fragment(q, limit, offset)
        return []


__all__ = ["WordLookupExecutor"]
