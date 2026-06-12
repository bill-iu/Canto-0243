"""C3：反義複合（!!）executor。把 CompoundAntQuery 導向 PositionMatchEngine + MatchSpec。

繼承 P-C1 RelationSyntaxExecutor 與 P-C2 WordLookupExecutor 的模式：
- 專屬 executor 持有 db
- 負責 !! 特有的 ant pair 候選來源
- 產出 MatchSpec（code_prefix + 可選 rhyme final_anchor）
- 委派 run_position_query（source + engine filter + 統一 serialize/sort）

（C3 已完成刪除 word_search_service.py）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_engine import CompoundAntQuery

from app.services.char_antonym_pairs import build_char_antonym_pairs
from app.services.position_match import CompoundAntCandidateSource, run_position_query


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
        """主入口：由 ant pair 產生專用 CandidateSource → MatchSpec → run_position_query。"""
        ant_pairs = build_char_antonym_pairs(self._db)
        if not ant_pairs:
            return []

        source = CompoundAntCandidateSource(self._db, ant_pairs)
        spec = parsed.to_match_spec()

        # 注意：rhyme 由 spec 的 final_anchor slot (pos=1) 在 engine 內 filter_candidates_by_match_spec 處理
        # code_prefix 由 source 在查詢時處理（與 legacy 一致）
        return run_position_query(
            spec,
            self._db,
            mode,
            limit,
            offset,
            source=source,
        )


__all__ = ["CompoundAntExecutor"]
