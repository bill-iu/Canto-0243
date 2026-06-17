"""近反義關係查詢 executor：PoolSnapshot 之後的 Word 列投影。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_parse import RelationLookupQuery
from app.domain.relations.pool_projection import relation_pool_chars, relation_pool_page
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_serializer import serialize_page
from app.utils.jyutping_codec import get_code_variants

from app.models.word import Word


def words_for_relation_chars(
    db: Session,
    ranked_chars: List[str],
    *,
    code_prefix: Optional[str],
    mode: str,
    limit: int,
    offset: int,
) -> List[dict]:
    """Map ranked relation chars to Word rows, optionally filtered by 0243 code prefix."""
    if not ranked_chars:
        return []

    char_order = {ch: idx for idx, ch in enumerate(dict.fromkeys(ranked_chars))}
    query = db.query(Word).filter(Word.char.in_(list(char_order.keys())))
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        query = query.filter(Word.code.in_(variants), length_filter(len(code_prefix)))

    words = query.all()
    words.sort(key=lambda w: (char_order.get(w.char or "", 10**9), w.code or "", w.jyutping or ""))
    return serialize_page(words, offset, limit, result_type="word")


class RelationSyntaxExecutor:
    """Per-request executor for 近反義模式 and ~ / ! 關係查詢。"""

    def __init__(self, db: Session, thesaurus: Optional[ThesaurusPort] = None):
        self._db = db
        self._thesaurus = thesaurus or default_thesaurus_port()

    def syn_mode_page(self, query: str, *, limit: int, offset: int) -> List[dict]:
        """mode=syn：full syn + ant + semantic 分頁列（近反義模式）。"""
        if not query or not re.search(r"[\u4e00-\u9fff]", query):
            return []
        return relation_pool_page(
            self._db,
            query.strip(),
            limit=limit,
            offset=offset,
            thesaurus=self._thesaurus,
        )

    def relation_lookup_page(
        self,
        parsed: RelationLookupQuery,
        *,
        mode: str,
        limit: int,
        offset: int,
    ) -> List[dict]:
        """~ / ! 近反義關係查詢：ranked chars → Word 列。"""
        ranked_chars = relation_pool_chars(
            self._db,
            parsed.word,
            parsed.relation_kind,
            thesaurus=self._thesaurus,
            expand_ant_via_syn=parsed.relation_kind == "ant",
        )
        return words_for_relation_chars(
            self._db,
            ranked_chars,
            code_prefix=parsed.code_prefix,
            mode=mode,
            limit=limit,
            offset=offset,
        )


__all__ = [
    "RelationSyntaxExecutor",
    "words_for_relation_chars",
]
