"""缺字型查詢執行 — 公開 API（ADR-0004 #1）。"""

from app.services.position_match.engine import execute_match_spec, run_equals_query
from app.services.position_match.spec import MaskFamilySearchResult, MatchSpec, SlotConstraint

__all__ = [
    "MatchSpec",
    "SlotConstraint",
    "execute_match_spec",
    "run_equals_query",
    "MaskFamilySearchResult",
]