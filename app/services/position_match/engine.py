"""PositionMatchEngine and query execution entry points."""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.domain.lexicon.ranking import search_result_sort_key
from app.services.position_match.filters import apply_match_spec
from app.services.position_match.sources import (
    _resolve_mask_family_source,
    get_candidates_for_length,
)
from app.services.position_match.spec import (
    CandidateSource,
    MaskFamilySearchResult,
    MatchSpec,
    get_equals_span,
)


class PositionMatchEngine:
    """集中處理所有位置型查詢的 deep module。"""

    def match(
        self,
        spec: MatchSpec,
        source: CandidateSource,
        db: Any,
        mode: str = "m1",
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        pre_candidates: Optional[list] = None,
    ) -> list[Any]:
        if pre_candidates is not None:
            candidates = pre_candidates
        elif source is None:
            candidates, _ = get_candidates_for_length(db, spec.width, code=spec.code_prefix, mode=mode)
        else:
            candidates, _ = source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)

        return apply_match_spec(spec, candidates, db, mode)


_DEFAULT_ENGINE = PositionMatchEngine()


def run_position_query(
    spec: MatchSpec,
    db: Any,
    mode: str,
    limit: int,
    offset: int,
    *,
    source: CandidateSource | None = None,
    pre_candidates: list[Any] | None = None,
    sort_key: Callable[[Any], Any] | None = None,
) -> list:
    items, _ = run_position_query_tracked(
        spec,
        db,
        mode,
        limit,
        offset,
        source=source,
        pre_candidates=pre_candidates,
        sort_key=sort_key,
    )
    return items


def run_position_query_tracked(
    spec: MatchSpec,
    db: Any,
    mode: str,
    limit: int,
    offset: int,
    *,
    source: CandidateSource | None = None,
    pre_candidates: list[Any] | None = None,
    sort_key: Callable[[Any], Any] | None = None,
) -> tuple[list, bool]:
    from app.services.word_serializer import serialize_page

    from_cache = False
    if get_equals_span(spec):
        filtered = apply_match_spec(spec, [], db, mode)
    elif pre_candidates is not None:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=pre_candidates)
    elif source is not None:
        candidates, from_cache = source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=candidates)
    else:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode)

    key = sort_key or search_result_sort_key
    filtered.sort(key=key)
    return serialize_page(filtered, offset, limit), from_cache


def execute_dual_phoneme_anchor_specs(
    initial_spec: MatchSpec,
    final_spec: MatchSpec,
    *,
    code: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    db: Any,
) -> MaskFamilySearchResult:
    """歧義 m／ng 粵拼錨：合併雙維結果並標 anchor_dimension。"""
    unpaged_limit = max(limit + offset, limit) + 500
    initial_result = execute_match_spec(
        initial_spec,
        code=code,
        mode=mode,
        limit=unpaged_limit,
        offset=0,
        db=db,
    )
    final_result = execute_match_spec(
        final_spec,
        code=code,
        mode=mode,
        limit=unpaged_limit,
        offset=0,
        db=db,
    )
    tagged: list = []
    for item in initial_result.items:
        tagged.append({**item, "anchor_dimension": "initial"})
    for item in final_result.items:
        tagged.append({**item, "anchor_dimension": "final"})
    page = tagged[offset : offset + limit]
    cache_path = initial_result.cache_path or final_result.cache_path
    return MaskFamilySearchResult(items=page, cache_path=cache_path)


def execute_match_spec(
    spec: MatchSpec,
    *,
    code: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    db: Any,
) -> MaskFamilySearchResult:
    if spec is None or spec.width == 0:
        return MaskFamilySearchResult(items=[])

    if spec.extra.get("dual_phoneme"):
        return execute_dual_phoneme_anchor_specs(
            spec.extra["dual_initial_spec"],
            spec.extra["dual_final_spec"],
            code=code,
            mode=mode,
            limit=limit,
            offset=offset,
            db=db,
        )

    source, sort_key = _resolve_mask_family_source(spec, db, mode, code)
    has_phoneme_anchors = any(
        s.kind in ("final_anchor", "initial_anchor") for s in spec.slots
    )
    if not get_equals_span(spec) and source is None and not has_phoneme_anchors:
        return MaskFamilySearchResult(items=[])

    items, from_cache = run_position_query_tracked(
        spec, db, mode, limit, offset, source=source, sort_key=sort_key
    )
    cache_path = "fallback" if get_equals_span(spec) or not from_cache else "ready"
    return MaskFamilySearchResult(items=items, cache_path=cache_path)
