"""Query parse + dispatch for 詞條搜尋.

Parse is pure (no DB). Execute delegates to existing handlers (migration phase C1).
Priority order in parse_query is semantic — do not reorder without regression tests.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import List, Literal, Optional, Union

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.word_db_filters import apply_code_filter
from app.services.word_query_parser import (
    hybrid_query_from_tail_equals,
    is_framed_equals_query,
    is_hybrid_tail_equals_alias,
    looks_like_mask_query,
    normalize_code_tail_separators,
    parse_at_tail_query,
    parse_code_tail_query,
    parse_relation_syntax,
    parse_rhyme_anchor_query,
)
from app.services.word_serializer import deduplicate_words


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

    def to_handler_dict(self) -> dict:
        return {
            "kind": "compound_ant",
            "code_prefix": self.code_prefix,
            "rhyme_char": self.rhyme_char,
        }


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

    def to_match_spec(self) -> 'MatchSpec':
        """Normalize this code-tail parsed query to engine MatchSpec (Phase 2.3).
        Encapsulates literal vs phoneme anchor logic and mask construction.
        """
        from app.services.position_match import MatchSpec, SlotConstraint
        from app.services.word_query_parser import build_mask_from_slots
        spec = MatchSpec(width=self.width, code_prefix=self.code_digits)
        if self.constraint == "literal":
            m = build_mask_from_slots("", self.width, self.anchor_pos)
            m = m[:self.anchor_pos] + self.anchor
            spec.mask = m
            spec.slots.append(SlotConstraint(pos=self.anchor_pos, kind="literal_char", value=self.anchor))
        else:
            kind = "final_anchor" if self.constraint == "final" else "initial_anchor"
            spec.slots.append(SlotConstraint(pos=self.anchor_pos, kind=kind, value=self.anchor))
            m = build_mask_from_slots("", self.width, self.anchor_pos)
            spec.mask = m
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

    def to_match_spec(self) -> 'MatchSpec':
        """Normalize this literal-ref (at-tail) parsed query to engine MatchSpec (Phase 2.3)."""
        from app.services.position_match import MatchSpec, SlotConstraint
        spec = MatchSpec(width=self.width, code_prefix=self.code_digits)
        spec.slots.append(SlotConstraint(pos=self.width-1, kind="literal_char", value=self.literal_char))
        spec.mask = "?" * (self.width - 1) + self.literal_char
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

    def to_match_spec(self) -> 'MatchSpec':
        """Normalize this rhyme-anchor parsed query to engine MatchSpec (Phase 2.3)."""
        from app.services.position_match import MatchSpec, SlotConstraint
        from app.services.word_query_parser import build_mask_from_slots
        spec = MatchSpec(width=self.width)
        kind = "final_anchor" if self.constraint == "final" else "initial_anchor"
        spec.slots.append(SlotConstraint(
            pos=self.anchor_pos,
            kind=kind,
            value=self.anchor
        ))
        spec.mask = build_mask_from_slots(self.slots, self.width, self.anchor_pos)
        return spec


@dataclass(frozen=True)
class HybridCodeQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.HYBRID_CODE


@dataclass(frozen=True)
class MaskQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.MASK


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

_HYBRID_CODE_RE = re.compile(r"^(\d+)([一-龥]+)(\d*)$")


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

    hybrid_match = _HYBRID_CODE_RE.match(q)
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


@dataclass
class SearchContext:
    q: Optional[str]
    code: Optional[str]
    char: Optional[str]
    mode: str
    limit: int
    offset: int
    db: Session


class QueryEngine:
    """Deep module: parse + ordered dispatch for 詞條搜尋."""

    def execute(self, ctx: SearchContext) -> list:
        if not ctx.q:
            return self._execute_list_filter(ctx)

        q = normalize_code_tail_separators(ctx.q.strip())

        if ctx.mode == "syn":
            from app.services.word_search_service import handle_syn_ant_search

            return handle_syn_ant_search(q, ctx.db, limit=ctx.limit, offset=ctx.offset)

        parsed = parse_query(q)
        return self._dispatch(parsed, q, ctx)

    def _execute_list_filter(self, ctx: SearchContext) -> list:
        query = ctx.db.query(Word)
        query = apply_code_filter(query, ctx.code, ctx.mode)
        if ctx.char:
            query = query.filter(Word.char == ctx.char)
        results = query.order_by(Word.char).offset(ctx.offset).limit(ctx.limit).all()
        return deduplicate_words(results)

    def _dispatch(self, parsed: ParsedQuery, q: str, ctx: SearchContext) -> list:
        from app.services.mask_search import (
            handle_at_tail_query,
            handle_code_tail_query,
            handle_hybrid_syntax,
            handle_mask_wildcard_query,
            handle_rhyme_anchor_query,
        )
        from app.services.word_search_service import (
            handle_antonym_compound_syntax,
            handle_equals_syntax,
            handle_jyut_fragment_query,
            handle_pure_canto_query,
            handle_pure_digit_query,
            handle_relation_lookup_syntax,
        )

        code = ctx.code
        mode = ctx.mode
        limit = ctx.limit
        offset = ctx.offset
        db = ctx.db

        # Phase 2.2: registry for dispatch cohesion (reduce big isinstance ladder)
        # Map type -> lambda(parsed, code, mode, limit, offset, db) that extracts arg and calls handler
        # This makes dispatch data-driven, easy to extend, no long if-chain.
        handler_registry = {
            RelationLookupQuery: lambda p, c, m, l, o, d: handle_relation_lookup_syntax(p.to_handler_dict(), m, l, o, d),
            CompoundAntQuery: lambda p, c, m, l, o, d: handle_antonym_compound_syntax(p.to_handler_dict(), m, l, o, d),
            CodeTailQuery: lambda p, c, m, l, o, d: handle_code_tail_query(p, m, l, o, d),
            LiteralRefQuery: lambda p, c, m, l, o, d: handle_at_tail_query(p, m, l, o, d),
            RhymeAnchorQuery: lambda p, c, m, l, o, d: handle_rhyme_anchor_query(p, m, l, o, d),
            DigitCodeQuery: lambda p, c, m, l, o, d: handle_pure_digit_query(p.raw_q, c, m, l, o, d),
            MaskQuery: lambda p, c, m, l, o, d: handle_mask_wildcard_query(p.raw_q, c, m, l, o, d),
            HybridTailEqualsAliasQuery: lambda p, c, m, l, o, d: handle_hybrid_syntax(p.hybrid_q, c, m, l, o, d),
            EqualsQuery: lambda p, c, m, l, o, d: handle_equals_syntax(p.raw_q, c, m, l, o, d),
            HybridCodeQuery: lambda p, c, m, l, o, d: handle_hybrid_syntax(p.raw_q, c, m, l, o, d),
        }

        handler = handler_registry.get(type(parsed))
        if handler:
            return handler(parsed, code, mode, limit, offset, db)

        if isinstance(parsed, WordLookupQuery):
            res = handle_pure_canto_query(parsed.raw_q, code, mode, limit, offset, db)
            if res:
                return res
            if re.search(r"[a-zA-Z]", parsed.raw_q):
                return handle_jyut_fragment_query(parsed.raw_q, limit, offset, db)
            return []

        if isinstance(parsed, JyutpingFragmentQuery):
            return handle_jyut_fragment_query(parsed.raw_q, limit, offset, db)

        return []


_default_engine = QueryEngine()


def execute_search(ctx: SearchContext) -> list:
    return _default_engine.execute(ctx)
