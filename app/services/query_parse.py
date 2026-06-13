"""Pure query classification — CONTEXT § 查詢分派（parse 優先序）."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal, Optional, Union

from app.services.word_query_parser import (
    hybrid_query_from_tail_equals,
    is_framed_equals_query,
    is_hybrid_tail_equals_alias,
    looks_like_mask_query,
    parse_at_tail_query,
    parse_code_tail_query,
    parse_relation_syntax,
    parse_rhyme_anchor_query,
)


class QueryKind(str, Enum):
    """Parsed query classification (domain syntax types)."""

    RELATION_LOOKUP = "relation_lookup"
    COMPOUND_ANT = "compound_ant"
    HYBRID_TAIL_EQUALS_ALIAS = "hybrid_tail_equals_alias"
    EQUALS = "equals"
    CODE_TAIL = "code_tail"
    LITERAL_REF = "literal_ref"
    RHYME_ANCHOR = "rhyme_anchor"
    HYBRID_CODE = "hybrid_code"
    MASK = "mask"
    DIGIT_CODE = "digit_code"
    WORD_LOOKUP = "word_lookup"
    JYUTPING_FRAGMENT = "jyutping_fragment"
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class RelationLookupQuery:
    relation_kind: Literal["syn", "ant"]
    word: str
    code_prefix: Optional[str] = None

    @property
    def kind(self) -> QueryKind:
        return QueryKind.RELATION_LOOKUP

    def to_handler_dict(self) -> dict:
        return {
            "kind": self.relation_kind,
            "word": self.word,
            "code_prefix": self.code_prefix,
        }


@dataclass(frozen=True)
class CompoundAntQuery:
    code_prefix: Optional[str]
    rhyme_char: Optional[str]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.COMPOUND_ANT

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid compound ant query: {self!r}")
        return spec


@dataclass(frozen=True)
class HybridTailEqualsAliasQuery:
    raw_q: str
    hybrid_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.HYBRID_TAIL_EQUALS_ALIAS


@dataclass(frozen=True)
class EqualsQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.EQUALS

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid equals query: {self.raw_q!r}")
        return spec


@dataclass(frozen=True)
class CodeTailQuery:
    code_digits: str
    width: int
    constraint: str
    anchor: str
    anchor_pos: int

    @property
    def kind(self) -> QueryKind:
        return QueryKind.CODE_TAIL

    def to_handler_dict(self) -> dict:
        return asdict(self)

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid code tail query: {self!r}")
        return spec


@dataclass(frozen=True)
class LiteralRefQuery:
    code_digits: str
    literal_char: str
    width: int

    @property
    def kind(self) -> QueryKind:
        return QueryKind.LITERAL_REF

    def to_handler_dict(self) -> dict:
        return asdict(self)

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid literal ref query: {self!r}")
        return spec


@dataclass(frozen=True)
class RhymeAnchorQuery:
    constraint: str
    anchor_pos: int
    anchor: str
    slots: str
    width: int

    @property
    def kind(self) -> QueryKind:
        return QueryKind.RHYME_ANCHOR

    def to_handler_dict(self) -> dict:
        return asdict(self)

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid rhyme anchor query: {self!r}")
        return spec


@dataclass(frozen=True)
class HybridCodeQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.HYBRID_CODE

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid hybrid code query: {self.raw_q!r}")
        return spec


@dataclass(frozen=True)
class MaskQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.MASK

    def to_match_spec(self) -> "MatchSpec":
        from app.services.match_spec_factory import build_match_spec

        spec = build_match_spec(self)
        if spec is None:
            raise ValueError(f"invalid mask query: {self.raw_q!r}")
        return spec


@dataclass(frozen=True)
class DigitCodeQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.DIGIT_CODE


@dataclass(frozen=True)
class WordLookupQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.WORD_LOOKUP


@dataclass(frozen=True)
class JyutpingFragmentQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.JYUTPING_FRAGMENT


@dataclass(frozen=True)
class UnmatchedQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.UNMATCHED


ParsedQuery = Union[
    RelationLookupQuery,
    CompoundAntQuery,
    HybridTailEqualsAliasQuery,
    EqualsQuery,
    CodeTailQuery,
    LiteralRefQuery,
    RhymeAnchorQuery,
    HybridCodeQuery,
    MaskQuery,
    DigitCodeQuery,
    WordLookupQuery,
    JyutpingFragmentQuery,
    UnmatchedQuery,
]

from app.services.match_spec_factory import HYBRID_CODE_RE


def parse_query(q: str) -> ParsedQuery:
    """Classify a normalized query string. No DB access."""
    relation_parsed = parse_relation_syntax(q)
    if relation_parsed:
        if relation_parsed["kind"] == "compound_ant":
            return CompoundAntQuery(
                code_prefix=relation_parsed.get("code_prefix"),
                rhyme_char=relation_parsed.get("rhyme_char"),
            )
        return RelationLookupQuery(
            relation_kind=relation_parsed["kind"],
            word=relation_parsed["word"],
            code_prefix=relation_parsed.get("code_prefix"),
        )

    if is_hybrid_tail_equals_alias(q):
        return HybridTailEqualsAliasQuery(raw_q=q, hybrid_q=hybrid_query_from_tail_equals(q))

    if is_framed_equals_query(q):
        return EqualsQuery(raw_q=q)

    code_tail_parsed = parse_code_tail_query(q)
    if code_tail_parsed:
        return CodeTailQuery(**code_tail_parsed)

    at_tail_parsed = parse_at_tail_query(q)
    if at_tail_parsed:
        return LiteralRefQuery(**at_tail_parsed)

    rhyme_anchor_parsed = parse_rhyme_anchor_query(q)
    if rhyme_anchor_parsed:
        return RhymeAnchorQuery(**rhyme_anchor_parsed)

    hybrid_match = HYBRID_CODE_RE.match(q)
    if hybrid_match and not hybrid_match.group(3):
        return HybridCodeQuery(raw_q=q)

    if looks_like_mask_query(q):
        return MaskQuery(raw_q=q)

    if q.isdigit():
        return DigitCodeQuery(raw_q=q)

    if re.search(r"[\u4e00-\u9fff]", q):
        return WordLookupQuery(raw_q=q)

    if re.search(r"[a-zA-Z]", q):
        return JyutpingFragmentQuery(raw_q=q)

    return UnmatchedQuery(raw_q=q)
