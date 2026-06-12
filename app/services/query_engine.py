"""Query parse + dispatch for 詞條搜尋.

Parse is pure (no DB). Execute dispatches via registry to position / equals / lookup handlers.
Priority order in parse_query is semantic — do not reorder without regression tests.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import List, Literal, Optional, Union

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.essay_sort import sort_words
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

    def to_match_spec(self) -> "MatchSpec":
        """Normalize !! compound-ant query to PositionMatchEngine MatchSpec (C3).

        - width fixed at 2 (ant pair compounds are 2-char)
        - code_prefix applied as global filter (via source or spec)
        - rhyme_char (if present) → final_anchor on the *last* char of the compound (pos 1)
        """
        from app.services.position_match import MatchSpec, SlotConstraint

        spec = MatchSpec(width=2, code_prefix=self.code_prefix)
        if self.rhyme_char:
            spec.slots.append(
                SlotConstraint(
                    pos=1,  # last position in 2-char result
                    kind="final_anchor",
                    value=self.rhyme_char,
                )
            )
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

    def to_match_spec(self) -> "MatchSpec":
        """Normalize hybrid code query (e.g. 23就) to MatchSpec."""
        from app.services.position_match import MatchSpec

        hybrid_match = _HYBRID_CODE_RE.match(self.raw_q)
        if not hybrid_match:
            return MatchSpec(width=0)
        num_prefix = hybrid_match.group(1)
        ref_chars = hybrid_match.group(2)
        num_suffix = hybrid_match.group(3)
        full_code = num_prefix + num_suffix
        return MatchSpec(
            width=len(full_code),
            code_prefix=full_code,
            hybrid_ref_chars=ref_chars,
            hybrid_ref_pos=max(0, len(num_prefix) - 1),
        )


@dataclass(frozen=True)
class MaskQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.MASK

    def to_match_spec(self) -> 'MatchSpec':
        """Normalize 缺字查詢 to MatchSpec (Phase 2.6)."""
        from app.services.position_match import MatchSpec, SlotConstraint
        from app.services.word_query_parser import parse_mask_query

        expected_len, _, literal_positions = parse_mask_query(self.raw_q)
        spec = MatchSpec(
            width=expected_len,
            literal_priority=True,
            mask=self.raw_q,
        )
        for i, ch in enumerate(self.raw_q):
            if ch.isdigit():
                spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=ch))
        spec.extra["literal_positions"] = literal_positions
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

_HYBRID_CODE_RE = re.compile(r"^(\d+)([一-龥]+)(\d*)$")


def _dispatch_code_tail(parsed: CodeTailQuery, mode: str, limit: int, offset: int, db: Session) -> list:
    spec = parsed.to_match_spec()
    from app.services.position_match import LengthMaskCandidateSource, run_position_query

    return run_position_query(
        spec, db, mode, limit, offset, source=LengthMaskCandidateSource(db, spec.mask)
    )


def _dispatch_literal_ref(parsed: LiteralRefQuery, mode: str, limit: int, offset: int, db: Session) -> list:
    spec = parsed.to_match_spec()
    from app.services.position_match import LengthMaskCandidateSource, run_position_query

    return run_position_query(
        spec, db, mode, limit, offset, source=LengthMaskCandidateSource(db, spec.mask)
    )


def _dispatch_rhyme_anchor(parsed: RhymeAnchorQuery, mode: str, limit: int, offset: int, db: Session) -> list:
    spec = parsed.to_match_spec()
    from app.services.position_match import LengthMaskCandidateSource, run_position_query

    return run_position_query(
        spec, db, mode, limit, offset, source=LengthMaskCandidateSource(db, spec.mask)
    )


def _dispatch_hybrid_code(
    parsed: HybridCodeQuery,
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> list:
    spec = parsed.to_match_spec()
    if spec.width == 0:
        return []
    from app.services.position_match import LengthCodeCandidateSource, run_position_query

    return run_position_query(
        spec,
        db,
        mode,
        limit,
        offset,
        source=LengthCodeCandidateSource(db, code=spec.code_prefix, mode=mode),
    )


def _dispatch_hybrid_q(q: str, mode: str, limit: int, offset: int, db: Session) -> list:
    return _dispatch_hybrid_code(HybridCodeQuery(raw_q=q), mode, limit, offset, db)


def _dispatch_mask_wildcard(
    parsed: MaskQuery,
    code: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> list:
    from app.services.position_match import MaskWildcardCandidateSource, mask_priority_key, run_position_query

    spec = parsed.to_match_spec()
    if spec.width == 0:
        return []
    if code:
        spec.code_prefix = code
    literal_positions = spec.extra.get("literal_positions", [])
    source = MaskWildcardCandidateSource(db, spec.mask, mode=mode, query_code=spec.code_prefix)
    sort_key = lambda w: mask_priority_key(w, literal_positions)
    return run_position_query(spec, db, mode, limit, offset, source=source, sort_key=sort_key)


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
    total: Optional[int] = None


class QueryEngine:
    """Deep module: parse + ordered dispatch for 詞條搜尋."""

    def execute(self, ctx: SearchContext) -> list:
        if not ctx.q:
            return self._execute_list_filter(ctx)

        q = normalize_code_tail_separators(ctx.q.strip())

        if ctx.mode == "syn":
            from app.services.relation_syntax_executor import RelationSyntaxExecutor

            return RelationSyntaxExecutor(ctx.db).syn_mode_page(
                q, limit=ctx.limit, offset=ctx.offset
            )

        parsed = parse_query(q)
        return self._dispatch(parsed, q, ctx)

    def _execute_list_filter(self, ctx: SearchContext) -> list:
        query = ctx.db.query(Word)
        query = apply_code_filter(query, ctx.code, ctx.mode)
        if ctx.char:
            query = query.filter(Word.char == ctx.char)
        results = query.all()
        return sort_words(deduplicate_words(results))[ctx.offset : ctx.offset + ctx.limit]

    def _dispatch(self, parsed: ParsedQuery, q: str, ctx: SearchContext) -> list:
        from app.services.equals_query_handler import handle_equals_syntax
        from app.services.relation_syntax_executor import RelationSyntaxExecutor
        from app.services.word_lookup_executor import WordLookupExecutor
        from app.services.compound_ant_executor import CompoundAntExecutor

        code = ctx.code
        mode = ctx.mode
        limit = ctx.limit
        offset = ctx.offset
        db = ctx.db
        relation_executor = RelationSyntaxExecutor(db)
        lookup_executor = WordLookupExecutor(db)
        compound_ant_executor = CompoundAntExecutor(db)

        if isinstance(parsed, DigitCodeQuery):
            items, total = lookup_executor.pure_digit(parsed.raw_q, code, mode, limit, offset)
            ctx.total = total
            return items

        handler_registry = {
            RelationLookupQuery: lambda p, c, m, l, o, d: relation_executor.relation_lookup_page(
                p, mode=m, limit=l, offset=o
            ),
            CompoundAntQuery: lambda p, c, m, l, o, d: compound_ant_executor.compound_ant_page(p, mode=m, limit=l, offset=o),
            CodeTailQuery: lambda p, c, m, l, o, d: _dispatch_code_tail(p, m, l, o, d),
            LiteralRefQuery: lambda p, c, m, l, o, d: _dispatch_literal_ref(p, m, l, o, d),
            RhymeAnchorQuery: lambda p, c, m, l, o, d: _dispatch_rhyme_anchor(p, m, l, o, d),
            MaskQuery: lambda p, c, m, l, o, d: _dispatch_mask_wildcard(p, c, m, l, o, d),
            HybridTailEqualsAliasQuery: lambda p, c, m, l, o, d: _dispatch_hybrid_q(p.hybrid_q, m, l, o, d),
            EqualsQuery: lambda p, c, m, l, o, d: handle_equals_syntax(p.raw_q, c, m, l, o, d),
            HybridCodeQuery: lambda p, c, m, l, o, d: _dispatch_hybrid_code(p, m, l, o, d),
            WordLookupQuery: lambda p, c, m, l, o, d: lookup_executor.lookup(p.raw_q, c, m, l, o),
            JyutpingFragmentQuery: lambda p, c, m, l, o, d: lookup_executor.jyut_fragment(p.raw_q, l, o),
        }

        handler = handler_registry.get(type(parsed))
        if handler:
            return handler(parsed, code, mode, limit, offset, db)

        return []


_default_engine = QueryEngine()
_last_search_total: Optional[int] = None


def execute_search(ctx: SearchContext) -> list:
    global _last_search_total
    _last_search_total = None
    results = _default_engine.execute(ctx)
    _last_search_total = ctx.total
    return results


def get_last_search_total() -> Optional[int]:
    return _last_search_total


def search_words(
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m1",
    limit: int = 100,
    offset: int = 0,
    *,
    db: Session,
):
    """Public search entry (alias of execute_search)."""
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
    )
