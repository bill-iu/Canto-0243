"""詞條 lookup executor：純數字、純字面、粵拼查詢與 WordLookup fallback。"""

from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.domain.lexicon.lookup_layout import build_lookup_layout
from app.domain.lexicon.ranking import search_result_sort_key, sort_search_results
from app.services.word_db_filters import apply_code_filter, length_filter
from app.domain.lexicon.word_inject import warm_ref_char_for_lookup
from app.services.jyutping_match import expected_word_length, matches_jyutping_query
from app.services.ping_zak import code_matches_ping_ze_pattern
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

    def ping_ze_serial(
        self,
        pattern: str,
        limit: int,
        offset: int,
    ) -> tuple[List[dict], int]:
        width = len(pattern)
        query = self._db.query(Word).filter(length_filter(width))
        words = deduplicate_words(query.all())
        matched = [
            w for w in words if code_matches_ping_ze_pattern(w.code or "", pattern)
        ]
        matched.sort(key=search_result_sort_key)
        page = paginate(matched, offset, limit)
        return [serialize_word(w) for w in page], len(matched)

    def pure_canto(
        self,
        q: str,
        code: Optional[str],
        mode: str,
        limit: int,
        offset: int,
    ) -> tuple[List[dict], int]:
        # 庫命中優先；缺庫用 admission 記憶體合成（唔寫庫 — ADR-0054 精神／詞條 lookup）
        raw_targets: List = self._db.query(Word).filter(Word.char == q).all()
        if not raw_targets and re.search(r"[\u4e00-\u9fff]", q):
            from app.domain.relations.compound_connect import compose_transient_words

            raw_targets = compose_transient_words(q)
        target_words = deduplicate_words(raw_targets)
        if target_words:
            if len(q) >= 1:
                warm_ref_char_for_lookup(q[-1], self._db)
            built = build_lookup_layout(q, raw_targets, self._db)
            return paginate(built, offset, limit), len(built)
        return [], 0

    def jyut_fragment(self, q: str, limit: int, offset: int) -> tuple[List[dict], int]:
        word_len = expected_word_length(q)
        if word_len is None:
            return [], 0

        query = self._db.query(Word).filter(length_filter(word_len))
        candidates = query.all()
        matched = [w for w in candidates if matches_jyutping_query(w.jyutping or "", q)]
        ordered = sort_search_results(deduplicate_words(matched))
        page = paginate(ordered, offset, limit)
        return [serialize_word(w) for w in page], len(ordered)

    def lookup(
        self,
        q: str,
        code: Optional[str],
        mode: str,
        limit: int,
        offset: int,
    ) -> tuple[List[dict], int]:
        """WordLookupQuery path：canto 優先，含字母則 fallback jyut。"""
        res, total = self.pure_canto(q, code, mode, limit, offset)
        if res or total:
            return res, total
        if re.search(r"[a-zA-Z]", q):
            return self.jyut_fragment(q, limit, offset)
        return [], 0


__all__ = ["WordLookupExecutor"]
