"""PositionMatchEngine and query execution entry points."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from app.domain.lexicon.reference_reading import equals_authoritative_row
from app.domain.lexicon.ranking import search_result_sort_key, sort_search_results
from app.models.word import Word
from app.services.position_match.filters import (
    build_final_options_at_positions,
    filter_candidates_by_match_spec,
    matches_equals_phoneme_span,
    matches_hybrid_ref_chars,
)
from app.services.position_match.sources import (
    _resolve_mask_family_source,
    get_candidates_for_length,
)
from app.services.position_match.spec import (
    CandidateSource,
    MaskFamilySearchResult,
    MatchSpec,
)
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import (
    get_words_for_length,
    is_word_cache_ready,
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

        if spec.hybrid_ref_chars is not None and spec.hybrid_ref_pos is not None:
            target_final_options = build_final_options_at_positions(
                spec.hybrid_ref_chars, spec.hybrid_ref_pos, spec.width, db
            )
            filtered = []
            allowed_full_codes = set(get_code_variants(spec.code_prefix or "", mode)) if spec.code_prefix else set()
            for word in candidates:
                word_code_str = get_word_sort_code(word)
                if spec.code_prefix and word_code_str not in allowed_full_codes:
                    continue
                word_finals = get_rhyme_finals(word)
                word_char = get_word_text(word)
                if matches_hybrid_ref_chars(
                    word_char, word_finals, spec.hybrid_ref_chars, spec.hybrid_ref_pos, target_final_options
                ):
                    filtered.append(word)
            return filtered

        return filter_candidates_by_match_spec(candidates, spec, mode, db)

    def _match_equals_whole_word(
        self,
        spec: MatchSpec,
        db: Any,
        mode: str,
        *,
        target: Any,
        target_parts: list,
        is_final: bool,
    ) -> list[Any]:
        full_code = spec.code_prefix or ""
        target_key = tuple(target_parts)
        cached = _equals_length_bucket_candidates(spec.width, full_code or None, mode)
        storage_field = "finals" if is_final else "initials"
        target_storage_key = _phoneme_storage_key(target, storage_field)

        if cached is not None:
            pool = cached
            if target_storage_key:
                pool = [
                    w
                    for w in pool
                    if _phoneme_storage_key(w, storage_field) == target_storage_key
                ]
            if is_final:
                return [w for w in pool if tuple(get_rhyme_finals(w)) == target_key]
            return [w for w in pool if tuple(get_word_parts(w, "initials")) == target_key]

        query = db.query(Word).filter(length_filter(spec.width))
        if full_code:
            query = apply_code_filter(query, full_code, mode)
        if is_final:
            db_literal = _phoneme_db_literal(target, "finals")
            if db_literal:
                query = query.filter(Word.finals == db_literal)
            return [
                w
                for w in query.all()
                if tuple(get_rhyme_finals(w)) == target_key
            ]
        db_literal = _phoneme_db_literal(target, "initials")
        if db_literal:
            query = query.filter(Word.initials == db_literal)
        return query.all()

    def match_equals(self, spec: MatchSpec, db: Any, mode: str = "m1") -> list[Any]:
        from app.utils.json_helpers import load_json_list

        if not spec.ref_literal:
            return []

        target = equals_authoritative_row(spec.ref_literal, db, allow_inject=True)
        if not target:
            return []

        is_final = spec.ref_dimension == "final"
        target_parts = (
            get_rhyme_finals(target)
            if is_final
            else load_json_list(target.initials)
        )
        full_code = spec.code_prefix or ""

        query = db.query(Word)
        query = apply_code_filter(query, full_code, mode)
        query = query.filter(length_filter(spec.width))

        if spec.whole_word_phoneme_match:
            return self._match_equals_whole_word(
                spec,
                db,
                mode,
                target=target,
                target_parts=target_parts,
                is_final=is_final,
            )

        candidates = query.limit(2000).all()
        return [
            word
            for word in candidates
            if matches_equals_phoneme_span(
                word,
                target_parts,
                spec.ref_start_pos,
                phoneme_anchor_only=spec.phoneme_anchor_only,
                ref_literal=spec.ref_literal,
                dimension=spec.ref_dimension,
            )
        ]


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
    if pre_candidates is not None:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=pre_candidates)
    elif source is not None:
        candidates, from_cache = source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=candidates)
    else:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode)

    key = sort_key or search_result_sort_key
    filtered.sort(key=key)
    return serialize_page(filtered, offset, limit), from_cache


def _word_stored_phoneme_json(word: Any, field: str):
    if isinstance(word, dict):
        return word.get(field)
    return getattr(word, field, None)


def _phoneme_storage_key(word: Any, field: str) -> tuple:
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, list):
        return tuple(raw)
    if isinstance(raw, str) and raw:
        from app.utils.json_helpers import load_json_list

        return tuple(load_json_list(raw))
    return ()


def _phoneme_db_literal(word: Any, field: str) -> str:
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return json.dumps(raw, ensure_ascii=False, separators=(", ", ": "))
    return ""


def _equals_length_bucket_candidates(
    width: int,
    code_prefix: Optional[str],
    mode: str,
) -> Optional[list]:
    if not is_word_cache_ready():
        return None
    candidates = get_words_for_length(width)
    if not code_prefix:
        return candidates
    variants = set(get_code_variants(code_prefix, mode))
    return [w for w in candidates if get_word_sort_code(w) in variants]


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

    if spec.ref_literal:
        from app.services.word_serializer import deduplicate_words, serialize_page

        filtered = _DEFAULT_ENGINE.match_equals(spec, db, mode)
        items = serialize_page(
            sort_search_results(deduplicate_words(filtered)),
            offset,
            limit,
        )
        return MaskFamilySearchResult(items=items, cache_path="fallback")

    source, sort_key = _resolve_mask_family_source(spec, db, mode, code)
    if source is None:
        return MaskFamilySearchResult(items=[])

    items, from_cache = run_position_query_tracked(
        spec, db, mode, limit, offset, source=source, sort_key=sort_key
    )
    return MaskFamilySearchResult(
        items=items,
        cache_path="ready" if from_cache else "fallback",
    )