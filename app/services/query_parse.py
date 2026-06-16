"""Pure query classification — CONTEXT § 查詢分派（parse 優先序）."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Literal, Optional, Union

from app.services.jyutping_anchor import parse_jyutping_anchor_query, rhyme_letters_resolve_ok
from app.services.word_query_parser import (
    build_mask_from_slots,
    hybrid_query_from_tail_equals,
    is_framed_equals_query,
    is_hybrid_tail_equals_alias,
    looks_like_mask_query,
    parse_at_tail_query,
    parse_code_tail_query,
    parse_mask_query,
    parse_relation_syntax,
    parse_rhyme_anchor_query,
    parse_triple_rhyme_anchor_query,
)

HYBRID_CODE_RE = re.compile(r"^(\d+)([一-龥]+)(\d*)$")


class QueryKind(str, Enum):
    """Parsed query classification (domain syntax types)."""

    RELATION_LOOKUP = "relation_lookup"
    COMPOUND_ANT = "compound_ant"
    COMPOUND_SYN = "compound_syn"
    HYBRID_TAIL_EQUALS_ALIAS = "hybrid_tail_equals_alias"
    EQUALS = "equals"
    CODE_TAIL = "code_tail"
    LITERAL_REF = "literal_ref"
    RHYME_ANCHOR = "rhyme_anchor"
    TRIPLE_RHYME_ANCHOR = "triple_rhyme_anchor"
    JYUTPING_ANCHOR = "jyutping_anchor"
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
class CompoundSynQuery:
    code_prefix: Optional[str]
    rhyme_char: Optional[str]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.COMPOUND_SYN


@dataclass(frozen=True)
class CompoundAntQuery:
    code_prefix: Optional[str]
    rhyme_char: Optional[str]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.COMPOUND_ANT


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


@dataclass(frozen=True)
class JyutpingAnchorQuery:
    raw_q: str
    width: int
    anchor_pos: int
    anchor_kind: Literal["initial_letters", "rhyme_letters", "syllable_letters"]
    anchor_value: str
    code_prefix: Optional[str] = None
    code_slots: Optional[list] = None
    equals_style: bool = False
    hybrid_rhyme: bool = False

    @property
    def kind(self) -> QueryKind:
        return QueryKind.JYUTPING_ANCHOR


@dataclass(frozen=True)
class TripleRhymeAnchorQuery:
    anchor: str
    anchor_pos: int
    width: int
    leading_slots: str
    constraint: Literal["final"] = "final"

    @property
    def kind(self) -> QueryKind:
        return QueryKind.TRIPLE_RHYME_ANCHOR

    def to_handler_dict(self) -> dict:
        return asdict(self)


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
    hint: Optional[str] = None

    @property
    def kind(self) -> QueryKind:
        return QueryKind.UNMATCHED


ParsedQuery = Union[
    RelationLookupQuery,
    CompoundSynQuery,
    CompoundAntQuery,
    HybridTailEqualsAliasQuery,
    EqualsQuery,
    CodeTailQuery,
    LiteralRefQuery,
    RhymeAnchorQuery,
    TripleRhymeAnchorQuery,
    JyutpingAnchorQuery,
    HybridCodeQuery,
    MaskQuery,
    DigitCodeQuery,
    WordLookupQuery,
    JyutpingFragmentQuery,
    UnmatchedQuery,
]


JYUTPING_ANCHOR_INVALID_HINT = (
    "粵拼錨無效：韻母片段喺收錄讀音中搵唔到對應。請檢查拼寫或改用漢字錨。"
)


def parse_query(q: str) -> ParsedQuery:
    """Classify a normalized query string. No DB access."""
    relation_parsed = parse_relation_syntax(q)
    if relation_parsed:
        if relation_parsed["kind"] == "compound_syn":
            return CompoundSynQuery(
                code_prefix=relation_parsed.get("code_prefix"),
                rhyme_char=relation_parsed.get("rhyme_char"),
            )
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

    triple_rhyme_parsed = parse_triple_rhyme_anchor_query(q)
    if triple_rhyme_parsed:
        return TripleRhymeAnchorQuery(**triple_rhyme_parsed)

    jyutping_anchor_parsed = parse_jyutping_anchor_query(q)
    if jyutping_anchor_parsed:
        if jyutping_anchor_parsed.get("anchor_kind") == "rhyme_letters":
            if not rhyme_letters_resolve_ok(jyutping_anchor_parsed["anchor_value"]):
                return UnmatchedQuery(raw_q=q, hint=JYUTPING_ANCHOR_INVALID_HINT)
        return JyutpingAnchorQuery(**jyutping_anchor_parsed)

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


def is_mask_family_query(parsed: Any) -> bool:
    """是否為缺字型查詢家族（不含 ~~ / !! 複合詞）。"""
    return isinstance(
        parsed,
        (
            HybridTailEqualsAliasQuery,
            EqualsQuery,
            MaskQuery,
            HybridCodeQuery,
            RhymeAnchorQuery,
            TripleRhymeAnchorQuery,
            JyutpingAnchorQuery,
            CodeTailQuery,
            LiteralRefQuery,
        ),
    )


def _rewrite_mask_family_aliases(parsed: ParsedQuery) -> ParsedQuery:
    """別名改寫（如 HybridTailEqualsAlias → HybridCode），在正規化開頭完成。"""
    if isinstance(parsed, HybridTailEqualsAliasQuery):
        return HybridCodeQuery(raw_q=parsed.hybrid_q)
    return parsed


def build_equals_match_spec(q: str) -> Optional["MatchSpec"]:
    """查詢字串 → 等號 MatchSpec（純函式，無 DB）。語意見 CONTEXT § 碼夾等號查詢。"""
    from app.services.position_match import MatchSpec

    match = re.match(r"^(\d*)(=)?([一-龥]+)?(=)?(\d*)$", q)
    if not match:
        return None
    target_str = match.group(3) or ""
    if not target_str:
        return None

    left_code = match.group(1) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_equal = bool(match.group(2))
    target_length = len(target_str)
    expected_length = len(left_code) + len(right_code) or target_length
    start_pos = max(0, len(left_code) - target_length)
    full_code = left_code + right_code

    return MatchSpec(
        width=expected_length,
        code_prefix=full_code if full_code else None,
        ref_literal=target_str,
        ref_start_pos=start_pos,
        ref_dimension="final" if right_equal else "initial",
        phoneme_anchor_only=bool(left_code and (right_code or inner_equal)),
        whole_word_phoneme_match=(start_pos == 0 and target_length == expected_length),
    )


def _build_mask_family_match_spec(parsed: ParsedQuery) -> Optional["MatchSpec"]:
    """缺字家族 ParsedQuery → MatchSpec。無 DB。"""
    from app.services.position_match import MatchSpec, SlotConstraint

    if isinstance(parsed, EqualsQuery):
        return build_equals_match_spec(parsed.raw_q)

    if isinstance(parsed, CodeTailQuery):
        spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_digits)
        if parsed.constraint == "literal":
            m = build_mask_from_slots("", parsed.width, parsed.anchor_pos)
            m = m[: parsed.anchor_pos] + parsed.anchor
            spec.mask = m
            spec.slots.append(
                SlotConstraint(pos=parsed.anchor_pos, kind="literal_char", value=parsed.anchor)
            )
        else:
            kind = "final_anchor" if parsed.constraint == "final" else "initial_anchor"
            spec.slots.append(
                SlotConstraint(pos=parsed.anchor_pos, kind=kind, value=parsed.anchor)
            )
            spec.mask = build_mask_from_slots("", parsed.width, parsed.anchor_pos)
        return spec

    if isinstance(parsed, LiteralRefQuery):
        spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_digits)
        spec.slots.append(
            SlotConstraint(pos=parsed.width - 1, kind="literal_char", value=parsed.literal_char)
        )
        spec.mask = "?" * (parsed.width - 1) + parsed.literal_char
        return spec

    if isinstance(parsed, RhymeAnchorQuery):
        spec = MatchSpec(width=parsed.width)
        kind = "final_anchor" if parsed.constraint == "final" else "initial_anchor"
        spec.slots.append(
            SlotConstraint(pos=parsed.anchor_pos, kind=kind, value=parsed.anchor)
        )
        spec.mask = build_mask_from_slots(parsed.slots, parsed.width, parsed.anchor_pos)
        return spec

    if isinstance(parsed, TripleRhymeAnchorQuery):
        spec = MatchSpec(width=parsed.width)
        spec.slots.append(
            SlotConstraint(
                pos=parsed.anchor_pos,
                kind="final_anchor",
                value=parsed.anchor,
            )
        )
        spec.mask = "?" * parsed.width
        return spec

    if isinstance(parsed, JyutpingAnchorQuery):
        spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_prefix)
        spec.mask = "?" * parsed.width
        spec.slots.append(
            SlotConstraint(
                pos=parsed.anchor_pos,
                kind=parsed.anchor_kind,
                value=parsed.anchor_value,
            )
        )
        if parsed.code_slots:
            for pos, digit in parsed.code_slots:
                spec.slots.append(SlotConstraint(pos=pos, kind="code_digit", value=digit))
        elif parsed.code_prefix and parsed.width == len(parsed.code_prefix):
            for i, d in enumerate(parsed.code_prefix):
                spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=d))
        return spec

    if isinstance(parsed, HybridCodeQuery):
        hybrid_match = HYBRID_CODE_RE.match(parsed.raw_q)
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

    if isinstance(parsed, MaskQuery):
        expected_len, _, literal_positions = parse_mask_query(parsed.raw_q)
        spec = MatchSpec(
            width=expected_len,
            literal_priority=True,
            mask=parsed.raw_q,
        )
        for i, ch in enumerate(parsed.raw_q):
            if ch.isdigit():
                spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=ch))
        spec.extra["literal_positions"] = literal_positions
        return spec

    return None


def normalize_to_match_spec(parsed: ParsedQuery) -> Optional["MatchSpec"]:
    """查詢分派：ParsedQuery → MatchSpec（含別名改寫）。無 DB。"""
    from app.services.position_match import MatchSpec, SlotConstraint

    parsed = _rewrite_mask_family_aliases(parsed)

    mask_spec = _build_mask_family_match_spec(parsed)
    if mask_spec is not None:
        return mask_spec

    if isinstance(parsed, CompoundSynQuery):
        spec = MatchSpec(width=2, code_prefix=parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(
                    pos=1,
                    kind="final_anchor",
                    value=parsed.rhyme_char,
                )
            )
        return spec

    if isinstance(parsed, CompoundAntQuery):
        spec = MatchSpec(width=2, code_prefix=parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(
                    pos=1,
                    kind="final_anchor",
                    value=parsed.rhyme_char,
                )
            )
        return spec

    return None


def build_match_spec(parsed: ParsedQuery) -> Optional["MatchSpec"]:
    """Alias for normalize_to_match_spec（過渡期）。"""
    return normalize_to_match_spec(parsed)
