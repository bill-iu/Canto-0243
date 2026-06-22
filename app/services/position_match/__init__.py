"""缺字型查詢執行 — 公開 API（ADR-0004 #1）。"""

from app.services.position_match.spec import MaskFamilySearchResult, MatchSpec, SlotConstraint


def execute_match_spec(*args, **kwargs):
    from app.services.position_match.engine import execute_match_spec as _run

    return _run(*args, **kwargs)


def execute_dual_phoneme_anchor_specs(*args, **kwargs):
    from app.services.position_match.engine import execute_dual_phoneme_anchor_specs as _run

    return _run(*args, **kwargs)


__all__ = [
    "MatchSpec",
    "SlotConstraint",
    "execute_match_spec",
    "execute_dual_phoneme_anchor_specs",
    "MaskFamilySearchResult",
]