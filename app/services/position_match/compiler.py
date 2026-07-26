"""Strict ParsedQuery → canonical MatchSpec compiler seam (migration shell)."""

from __future__ import annotations

from typing import TypeAlias

from app.services._generated.query_kind_registry import MATCH_SPEC_KINDS, QueryKind, uses_match_spec_kind
from app.services.position_match.canonical import CanonicalMatchSpec, canonicalize_legacy_match_spec
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_types import (
    CodeRefMiddleRhymeQuery,
    CompoundAntQuery,
    CompoundConnectAntQuery,
    CompoundConnectSynQuery,
    CompoundDoubledSyllableQuery,
    CompoundSynQuery,
    EqualsQuery,
    JyutpingAnchorQuery,
    LiteralRefQuery,
    MaskQuery,
    PartialInitialMaskQuery,
    PartialRhymeMaskQuery,
    ParsedQuery,
    PingZeSerialQuery,
    PlusAnchorQuery,
    PrefixWildcardEqualsQuery,
    RhymeAnchorQuery,
    SerialPhonemeAnchorQuery,
    TripleRhymeAnchorQuery,
    WildcardCodeAnchorQuery,
)

MatchSpecQuery: TypeAlias = (
    EqualsQuery
    | PrefixWildcardEqualsQuery
    | PartialRhymeMaskQuery
    | PartialInitialMaskQuery
    | SerialPhonemeAnchorQuery
    | PlusAnchorQuery
    | LiteralRefQuery
    | WildcardCodeAnchorQuery
    | CodeRefMiddleRhymeQuery
    | RhymeAnchorQuery
    | TripleRhymeAnchorQuery
    | JyutpingAnchorQuery
    | MaskQuery
    | PingZeSerialQuery
    | CompoundSynQuery
    | CompoundConnectSynQuery
    | CompoundDoubledSyllableQuery
    | CompoundAntQuery
    | CompoundConnectAntQuery
)


def require_match_spec_query(parsed: ParsedQuery) -> MatchSpecQuery:
    """Narrow general parser output at the query dispatch seam."""
    if not uses_match_spec_kind(parsed.kind):
        raise ValueError(f"query kind does not use MatchSpec: {parsed.kind}")
    return parsed  # type: ignore[return-value]


def compile_query(query: MatchSpecQuery) -> CanonicalMatchSpec:
    """Compile one eligible query to a complete semantic value."""
    if query.kind not in MATCH_SPEC_KINDS:
        raise ValueError(f"query kind does not use MatchSpec: {query.kind}")
    legacy = build_match_spec_for_parsed(query)
    if legacy is None:
        raise ValueError(f"MatchSpec compiler has no implementation for {query.kind}")
    return canonicalize_legacy_match_spec(legacy)


def compile_parsed_query(parsed: ParsedQuery) -> CanonicalMatchSpec:
    return compile_query(require_match_spec_query(parsed))


MATCH_SPEC_QUERY_KINDS = frozenset(MATCH_SPEC_KINDS)


__all__ = [
    "MATCH_SPEC_QUERY_KINDS",
    "MatchSpecQuery",
    "compile_parsed_query",
    "compile_query",
    "require_match_spec_query",
]
