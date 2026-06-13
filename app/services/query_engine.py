"""Backward-compatible facade for query parse + dispatch.

Prefer importing from ``query_parse`` (pure) or ``query_dispatch`` (execute).
"""
from app.services.query_dispatch import (
    QueryEngine,
    SearchContext,
    SearchResult,
    execute_search,
    search_words,
)
from app.services.query_parse import (
    CodeTailQuery,
    CompoundAntQuery,
    DigitCodeQuery,
    EqualsQuery,
    HybridCodeQuery,
    HybridTailEqualsAliasQuery,
    JyutpingFragmentQuery,
    LiteralRefQuery,
    MaskQuery,
    ParsedQuery,
    QueryKind,
    RelationLookupQuery,
    RhymeAnchorQuery,
    UnmatchedQuery,
    WordLookupQuery,
    parse_query,
)

__all__ = [
    "CodeTailQuery",
    "CompoundAntQuery",
    "DigitCodeQuery",
    "EqualsQuery",
    "HybridCodeQuery",
    "HybridTailEqualsAliasQuery",
    "JyutpingFragmentQuery",
    "LiteralRefQuery",
    "MaskQuery",
    "ParsedQuery",
    "QueryEngine",
    "QueryKind",
    "RelationLookupQuery",
    "RhymeAnchorQuery",
    "SearchContext",
    "SearchResult",
    "UnmatchedQuery",
    "WordLookupQuery",
    "execute_search",
    "parse_query",
    "search_words",
]
