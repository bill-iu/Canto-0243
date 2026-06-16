"""C3：反義複合（!!）executor。把 CompoundAntQuery 導向 PositionMatchEngine + MatchSpec。

候選集來自 curated ``compound_antonyms.txt``（非全部 word_relations ant pair）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_parse import CompoundAntQuery

from dataclasses import dataclass
from typing import Any, Optional

from app.models.word import Word
from app.services.position_match.engine import run_position_query
from app.services.query_parse import build_match_spec
from app.lexicon.compound_antonyms import load_compound_antonyms
from app.services.word_db_filters import length_filter


@dataclass
class CompoundAntCandidateSource:
    """!! 反義複合專用候選來源（curated compound_antonyms.txt）。"""

    db: Any
    compounds: frozenset[str]

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        if length != 2 or not self.compounds:
            return [], True

        query = self.db.query(Word).filter(Word.char.in_(list(self.compounds)), length_filter(2))
        rows = query.order_by(Word.char, Word.code, Word.jyutping).all()
        return rows, False


class CompoundAntExecutor:
    """Per-request executor for !! / 33!! / !!你 / 33!!你 等反義複合查詢。"""

    def __init__(self, db: Session):
        self._db = db

    def compound_ant_page(
        self,
        parsed: CompoundAntQuery,
        *,
        mode: str,
        limit: int,
        offset: int,
    ) -> List[dict]:
        """主入口：curated compounds → MatchSpec → run_position_query。"""
        compounds = frozenset(load_compound_antonyms())
        if not compounds:
            return []

        source = CompoundAntCandidateSource(self._db, compounds)
        spec = build_match_spec(parsed)

        return run_position_query(
            spec,
            self._db,
            mode,
            limit,
            offset,
            source=source,
        )


__all__ = ["CompoundAntExecutor"]
