"""Query dispatch for 詞條搜尋 — registry + SearchResult (no global total state)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.domain.lexicon.ranking import sort_search_results
from app.services.position_match import execute_match_spec
from app.services.query_parse import (
    DigitCodeQuery,
    JYUTPING_ANCHOR_INVALID_HINT,
    JyutpingFragmentQuery,
    ParsedQuery,
    QueryKind,
    RelationLookupQuery,
    UnmatchedQuery,
    WordLookupQuery,
    normalize_and_parse,
    normalize_query,
    normalize_to_match_spec,
)
from app.services.word_db_filters import apply_code_filter
from app.services.word_serializer import deduplicate_words


@dataclass
class SearchContext:
    q: Optional[str]
    code: Optional[str]
    char: Optional[str]
    mode: str
    limit: int
    offset: int
    db: Session
    fallback_0243_mode: Optional[str] = None


@dataclass
class SearchResult:
    items: List
    total: Optional[int] = None
    hint: Optional[str] = None
    cache_path: Optional[str] = None
    effective_mode: Optional[str] = None


JYUTPING_SYN_MODE_HINT = (
    "近反義模式只支援漢字查詢。請改打漢字，或切換至 0243模式／02493模式 查粵拼。"
)


def _mask_family_search_result(parsed: ParsedQuery, ctx: SearchContext) -> SearchResult:
    """缺字型查詢執行 — 正規化在分派層，執行僅收 MatchSpec。"""
    spec = normalize_to_match_spec(parsed)
    if spec is None:
        return SearchResult(items=[])

    result = execute_match_spec(
        spec,
        code=ctx.code,
        mode=ctx.mode,
        limit=ctx.limit,
        offset=ctx.offset,
        db=ctx.db,
    )
    hint = None
    if not result.items:
        from app.services.query_grammar.equals import code_prefixed_whole_word_equals_empty_hint

        hint = code_prefixed_whole_word_equals_empty_hint(spec, ctx.db)
    return SearchResult(items=result.items, hint=hint, cache_path=result.cache_path)


class QueryEngine:
    """Deep module: parse + ordered dispatch for 詞條搜尋."""

    def execute(self, ctx: SearchContext) -> SearchResult:
        if not ctx.q:
            items = self._execute_list_filter(ctx)
            return SearchResult(items=items)

        q = normalize_query(ctx.q)

        if ctx.mode == "syn":
            from app.services.query_mode_dispatch import dispatch_syn_mode

            return dispatch_syn_mode(ctx, q, self)

        parsed = normalize_and_parse(ctx.q)
        return self._dispatch(parsed, ctx)

    def _execute_list_filter(self, ctx: SearchContext) -> list:
        query = ctx.db.query(Word)
        query = apply_code_filter(query, ctx.code, ctx.mode)
        if ctx.char:
            query = query.filter(Word.char == ctx.char)
        results = query.all()
        return sort_search_results(deduplicate_words(results))[ctx.offset : ctx.offset + ctx.limit]

    def _dispatch(self, parsed: ParsedQuery, ctx: SearchContext) -> SearchResult:
        from app.services.relation_syntax_executor import RelationSyntaxExecutor
        from app.services.word_lookup_executor import WordLookupExecutor
        from app.services.query_kind_registry import RouteKind, route_kind_for

        code = ctx.code
        mode = ctx.mode
        limit = ctx.limit
        offset = ctx.offset
        db = ctx.db
        relation_executor = RelationSyntaxExecutor(db)
        lookup_executor = WordLookupExecutor(db)

        route_kind = route_kind_for(parsed.kind)

        if route_kind == RouteKind.DIGIT:
            assert isinstance(parsed, DigitCodeQuery)
            items, total = lookup_executor.pure_digit(parsed.raw_q, code, mode, limit, offset)
            return SearchResult(items=items, total=total)

        if route_kind == RouteKind.MASK_FAMILY:
            return _mask_family_search_result(parsed, ctx)

        if route_kind == RouteKind.HETERONYM:
            from app.services.heteronym_code_executor import execute_heteronym_code_search
            from app.services.query_types import HeteronymCodeQuery

            assert isinstance(parsed, HeteronymCodeQuery)
            items = execute_heteronym_code_search(
                parsed, mode=mode, limit=limit, offset=offset, db=db
            )
            return SearchResult(items=items)

        if route_kind == RouteKind.RELATION:
            assert isinstance(parsed, RelationLookupQuery)
            result = relation_executor.relation_lookup_page(parsed, mode=mode, limit=limit, offset=offset)
            return SearchResult(items=result)

        if route_kind == RouteKind.LOOKUP:
            if parsed.kind == QueryKind.WORD_LOOKUP:
                assert isinstance(parsed, WordLookupQuery)
                items = lookup_executor.lookup(parsed.raw_q, code, mode, limit, offset)
                return SearchResult(items=items)
            assert parsed.kind == QueryKind.JYUTPING_FRAGMENT
            assert isinstance(parsed, JyutpingFragmentQuery)
            items = lookup_executor.jyut_fragment(parsed.raw_q, limit, offset)
            return SearchResult(items=items)

        if route_kind == RouteKind.UNMATCHED:
            assert isinstance(parsed, UnmatchedQuery)
            return SearchResult(items=[], hint=parsed.hint)

        return SearchResult(items=[])


_default_engine = QueryEngine()


def execute_search(ctx: SearchContext) -> SearchResult:
    from app.startup.readiness_gate import require_search_ready

    require_search_ready()
    return _default_engine.execute(ctx)


def search_words(
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m1",
    limit: int = 100,
    offset: int = 0,
    *,
    db: Session,
) -> list:
    """Public search entry — returns items only for backward compatibility."""
    return execute_search(
        SearchContext(
            q=q,
            code=code,
            char=char,
            mode=mode,
            limit=limit,
            offset=offset,
            db=db,
        )
    ).items
