"""Query dispatch for 詞條搜尋 — registry + SearchResult (no global total state)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.domain.lexicon.ranking import sort_search_results
from app.services.position_match import execute_dual_phoneme_anchor_specs, execute_match_spec
from app.services.query_parse import (
    DigitCodeQuery,
    JYUTPING_ANCHOR_INVALID_HINT,
    JyutpingAnchorQuery,
    JyutpingFragmentQuery,
    ParsedQuery,
    RelationLookupQuery,
    UnmatchedQuery,
    WordLookupQuery,
    build_jyutping_dual_match_specs,
    normalize_and_parse,
    normalize_query,
    normalize_to_match_spec,
    uses_match_spec,
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


@dataclass
class SearchResult:
    items: List
    total: Optional[int] = None
    hint: Optional[str] = None
    cache_path: Optional[str] = None


JYUTPING_SYN_MODE_HINT = (
    "近反義模式只支援漢字查詢。請改打漢字，或切換至 0243模式／02493模式 查粵拼。"
)


def _mask_family_search_result(parsed: ParsedQuery, ctx: SearchContext) -> SearchResult:
    """缺字型查詢執行 — 正規化在分派層，執行僅收 MatchSpec。"""
    if isinstance(parsed, JyutpingAnchorQuery) and parsed.dual_phoneme:
        initial_spec, final_spec = build_jyutping_dual_match_specs(parsed)
        result = execute_dual_phoneme_anchor_specs(
            initial_spec,
            final_spec,
            code=ctx.code,
            mode=ctx.mode,
            limit=ctx.limit,
            offset=ctx.offset,
            db=ctx.db,
        )
        return SearchResult(items=result.items, cache_path=result.cache_path)

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
    return SearchResult(items=result.items, cache_path=result.cache_path)


class QueryEngine:
    """Deep module: parse + ordered dispatch for 詞條搜尋."""

    def execute(self, ctx: SearchContext) -> SearchResult:
        if not ctx.q:
            items = self._execute_list_filter(ctx)
            return SearchResult(items=items)

        q = normalize_query(ctx.q)

        if ctx.mode == "syn":
            from app.services.jyutping_match import is_jyutping_query
            from app.services.relation_syntax_executor import RelationSyntaxExecutor

            if is_jyutping_query(q):
                return SearchResult(items=[], hint=JYUTPING_SYN_MODE_HINT)

            items = RelationSyntaxExecutor(ctx.db).syn_mode_page(
                q, limit=ctx.limit, offset=ctx.offset
            )
            return SearchResult(items=items)

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

        code = ctx.code
        mode = ctx.mode
        limit = ctx.limit
        offset = ctx.offset
        db = ctx.db
        relation_executor = RelationSyntaxExecutor(db)
        lookup_executor = WordLookupExecutor(db)

        if isinstance(parsed, DigitCodeQuery):
            items, total = lookup_executor.pure_digit(parsed.raw_q, code, mode, limit, offset)
            return SearchResult(items=items, total=total)

        if uses_match_spec(parsed):
            return _mask_family_search_result(parsed, ctx)

        handler_registry = {
            RelationLookupQuery: lambda p: relation_executor.relation_lookup_page(
                p, mode=mode, limit=limit, offset=offset
            ),
            WordLookupQuery: lambda p: lookup_executor.lookup(p.raw_q, code, mode, limit, offset),
            JyutpingFragmentQuery: lambda p: lookup_executor.jyut_fragment(p.raw_q, limit, offset),
        }

        handler = handler_registry.get(type(parsed))
        if handler:
            result = handler(parsed)
            if isinstance(result, SearchResult):
                return result
            return SearchResult(items=result)

        if isinstance(parsed, UnmatchedQuery):
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
