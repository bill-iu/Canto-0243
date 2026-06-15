"""Query dispatch for 詞條搜尋 — registry + SearchResult (no global total state)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.essay_sort import sort_words
from app.services.position_match import execute_mask_family_search
from app.services.mask_family_normalize import is_mask_family_query, normalize_mask_family_parsed
from app.services.query_parse import (
    CompoundAntQuery,
    CompoundSynQuery,
    DigitCodeQuery,
    JyutpingFragmentQuery,
    ParsedQuery,
    RelationLookupQuery,
    UnmatchedQuery,
    WordLookupQuery,
    parse_query,
)
from app.services.word_db_filters import apply_code_filter
from app.services.word_query_parser import normalize_code_tail_separators
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
    """缺字型查詢執行 — 單一入口（正規化在分派層）。"""
    parsed = normalize_mask_family_parsed(parsed)
    result = execute_mask_family_search(
        parsed,
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

        q = normalize_code_tail_separators(ctx.q.strip())

        if ctx.mode == "syn":
            from app.services.jyutping_match import is_jyutping_query
            from app.services.relation_syntax_executor import RelationSyntaxExecutor

            if is_jyutping_query(q):
                return SearchResult(items=[], hint=JYUTPING_SYN_MODE_HINT)

            items = RelationSyntaxExecutor(ctx.db).syn_mode_page(
                q, limit=ctx.limit, offset=ctx.offset
            )
            return SearchResult(items=items)

        parsed = parse_query(q)
        return self._dispatch(parsed, ctx)

    def _execute_list_filter(self, ctx: SearchContext) -> list:
        query = ctx.db.query(Word)
        query = apply_code_filter(query, ctx.code, ctx.mode)
        if ctx.char:
            query = query.filter(Word.char == ctx.char)
        results = query.all()
        return sort_words(deduplicate_words(results))[ctx.offset : ctx.offset + ctx.limit]

    def _dispatch(self, parsed: ParsedQuery, ctx: SearchContext) -> SearchResult:
        from app.services.compound_ant_executor import CompoundAntExecutor
        from app.services.compound_syn_executor import CompoundSynExecutor
        from app.services.relation_syntax_executor import RelationSyntaxExecutor
        from app.services.word_lookup_executor import WordLookupExecutor

        code = ctx.code
        mode = ctx.mode
        limit = ctx.limit
        offset = ctx.offset
        db = ctx.db
        relation_executor = RelationSyntaxExecutor(db)
        lookup_executor = WordLookupExecutor(db)
        compound_ant_executor = CompoundAntExecutor(db)
        compound_syn_executor = CompoundSynExecutor(db)

        if isinstance(parsed, DigitCodeQuery):
            items, total = lookup_executor.pure_digit(parsed.raw_q, code, mode, limit, offset)
            return SearchResult(items=items, total=total)

        if is_mask_family_query(parsed):
            return _mask_family_search_result(parsed, ctx)

        handler_registry = {
            RelationLookupQuery: lambda p: relation_executor.relation_lookup_page(
                p, mode=mode, limit=limit, offset=offset
            ),
            CompoundSynQuery: lambda p: compound_syn_executor.compound_syn_page(
                p, mode=mode, limit=limit, offset=offset
            ),
            CompoundAntQuery: lambda p: compound_ant_executor.compound_ant_page(
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
            return SearchResult(items=[])

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
