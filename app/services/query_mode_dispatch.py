"""搜尋模式分派 — 近反義模式 predicate table（#4；RouteKind registry 補充）。"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from app.services.query_dispatch import QueryEngine, SearchContext, SearchResult

SynModePredicate = Callable[[str, SearchContext], bool]
SynModeHandler = Callable[[SearchContext, str, QueryEngine], SearchResult]


def _pred_jyutping_reject(q: str, ctx: SearchContext) -> bool:
    from app.services.jyutping_match import is_jyutping_query

    return is_jyutping_query(q)


def _handle_jyutping_reject(ctx: SearchContext, q: str, engine: QueryEngine) -> SearchResult:
    from app.services.query_dispatch import JYUTPING_SYN_MODE_HINT

    return SearchResult(items=[], hint=JYUTPING_SYN_MODE_HINT)


def _pred_relation_redirect(q: str, ctx: SearchContext) -> bool:
    from app.services.query_mode_policy import plan_redirect

    return plan_redirect(
        q,
        current_mode="syn",
        fallback_0243_mode=ctx.fallback_0243_mode,
        detect="full",
    ).should_redirect


def _handle_relation_redirect(ctx: SearchContext, q: str, engine: QueryEngine) -> SearchResult:
    from app.services.query_mode_policy import plan_redirect
    from app.services.query_parse import normalize_and_parse

    plan = plan_redirect(
        q,
        current_mode="syn",
        fallback_0243_mode=ctx.fallback_0243_mode,
        detect="full",
        lang="zh",
    )
    effective = plan.effective_mode or "m1"
    redirected = replace(ctx, mode=effective, offset=0 if plan.reset_offset else ctx.offset)
    parsed = normalize_and_parse(ctx.q)
    result = engine.dispatch_parsed(parsed, redirected)
    return SearchResult(
        items=result.items,
        total=result.total,
        hint=plan.hint,
        cache_path=result.cache_path,
        effective_mode=effective,
    )


def _pred_pool_page(q: str, ctx: SearchContext) -> bool:
    return True


def _handle_pool_page(ctx: SearchContext, q: str, engine: QueryEngine) -> SearchResult:
    from app.services.relation_syntax_executor import RelationSyntaxExecutor

    items = RelationSyntaxExecutor(ctx.db).syn_mode_page(
        q, limit=ctx.limit, offset=ctx.offset
    )
    return SearchResult(items=items)


SYN_MODE_STEPS: tuple[tuple[str, SynModePredicate, SynModeHandler], ...] = (
    ("jyutping_reject", _pred_jyutping_reject, _handle_jyutping_reject),
    ("relation_redirect", _pred_relation_redirect, _handle_relation_redirect),
    ("pool_page", _pred_pool_page, _handle_pool_page),
)


def dispatch_syn_mode(ctx: SearchContext, q: str, engine: QueryEngine) -> SearchResult:
    for _name, pred, handler in SYN_MODE_STEPS:
        if pred(q, ctx):
            return handler(ctx, q, engine)
    return SearchResult(items=[])


__all__ = [
    "SYN_MODE_STEPS",
    "dispatch_syn_mode",
]
