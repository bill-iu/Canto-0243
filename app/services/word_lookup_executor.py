"""詞條 lookup executor：純數字、純字面、粵拼片段與 WordLookup fallback。"""

from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.code_aware_ranker import build_code_aware_results
from app.services.essay_sort import default_word_sort_key, sort_words
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_ensure_service import ensure_word_in_db
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
        words.sort(key=default_word_sort_key)
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
            built = build_code_aware_results(q, raw_targets, self._db)
            return paginate(built, offset, limit)
        return []

    def jyut_fragment(self, q: str, limit: int, offset: int) -> List[dict]:
        results = (
            self._db.query(Word)
            .filter(Word.jyutping.ilike(f"%{q}%"))
            .limit(500)
            .all()
        )
        ordered = sort_words(deduplicate_words(results))
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
