"""近義複合（~~）executor — 鏡像 CompoundAntExecutor。"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_parse import CompoundSynQuery

from app.domain.relations.compound_syn import (
    DEFAULT_SYN_NEIGHBOR_K,
    build_compound_syn_tiers,
)
from app.services.essay_sort import default_word_sort_key
from app.services.position_match import CompoundSynCandidateSource, run_position_query
from app.services.query_parse import build_match_spec
from app.services.word_serializer import get_word_text


class CompoundSynExecutor:
    """Per-request executor for ~~ / 33~~ / ~~你 / 33~~你 等近義複合查詢。"""

    def __init__(self, db: Session):
        self._db = db

    def compound_syn_page(
        self,
        parsed: CompoundSynQuery,
        *,
        mode: str,
        limit: int,
        offset: int,
    ) -> List[dict]:
        tiers = build_compound_syn_tiers(self._db, k=DEFAULT_SYN_NEIGHBOR_K)
        if not tiers:
            return []

        source = CompoundSynCandidateSource(self._db, frozenset(tiers.keys()))
        spec = build_match_spec(parsed)
        if spec is None:
            return []

        sort_key = lambda w: (tiers.get(get_word_text(w), 99), default_word_sort_key(w))
        return run_position_query(
            spec,
            self._db,
            mode,
            limit,
            offset,
            source=source,
            sort_key=sort_key,
        )


__all__ = ["CompoundSynExecutor"]
