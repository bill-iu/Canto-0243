"""近義複合（~~）executor — 鏡像 CompoundAntExecutor。"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_parse import CompoundSynQuery

from app.domain.relations.compound_syn import (
    DEFAULT_SYN_NEIGHBOR_K,
    narrow_compound_syn_literals,
    search_compound_syn,
)
from app.domain.lexicon.ranking import search_result_sort_key
from app.services.position_match.engine import run_position_query
from app.services.position_match.sources import CompoundSynCandidateSource
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
        tiers = search_compound_syn(self._db, k=DEFAULT_SYN_NEIGHBOR_K)
        if not tiers:
            return []

        spec = build_match_spec(parsed)
        if spec is None:
            return []

        literals = narrow_compound_syn_literals(
            frozenset(tiers.keys()),
            width=spec.width,
            rhyme_char=parsed.rhyme_char,
            db=self._db,
        )
        if not literals:
            return []

        source = CompoundSynCandidateSource(self._db, literals)

        sort_key = lambda w: (tiers.get(get_word_text(w), 99), search_result_sort_key(w))
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
