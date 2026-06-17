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
    normalize_search_query,
    parse_at_tail_query,
    slot_connector_syntax_error,
    parse_code_ref_middle_rhyme_query,
    parse_code_ref_rhyme_contradiction_hint,
    parse_double_wildcard_initial_query,
    parse_double_wildcard_rhyme_query,
    parse_relation_syntax,
    parse_rhyme_anchor_query,
    parse_prefix_wildcard_equals_query,
    parse_pure_chars_serial_hint,
    parse_serial_phoneme_anchor_query,
    parse_star_anchor_query,
    parse_triple_rhyme_anchor_query,
    parse_wildcard_code_anchor_query,
    prefix_wildcard_equals_missing_eq_hint,
)

HYBRID_CODE_RE = re.compile(r"^(\d+)([一-龥]+)(\d*)$")


class QueryKind(str, Enum):
    """Parsed query classification (domain syntax types)."""

    RELATION_LOOKUP = "relation_lookup"
    COMPOUND_ANT = "compound_ant"
    COMPOUND_SYN = "compound_syn"
    HYBRID_TAIL_EQUALS_ALIAS = "hybrid_tail_equals_alias"
    EQUALS = "equals"
    STAR_ANCHOR = "star_anchor"
    WILDCARD_CODE_ANCHOR = "wildcard_code_anchor"
    CODE_REF_MIDDLE_RHYME = "code_ref_middle_rhyme"
    SERIAL_PHONEME = "serial_phoneme"
    PREFIX_WILDCARD_EQUALS = "prefix_wildcard_equals"
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
class CompoundConnectSynQuery:
    code_prefix: Optional[str]
    connective: str
    rhyme_char: Optional[str]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.COMPOUND_SYN


@dataclass(frozen=True)
class CompoundConnectAntQuery:
    code_prefix: Optional[str]
    connective: str
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
class PrefixWildcardEqualsQuery:
    raw_q: str
    inner_q: str
    ref_literal: str
    width: int

    @property
    def kind(self) -> QueryKind:
        return QueryKind.PREFIX_WILDCARD_EQUALS


@dataclass(frozen=True)
class SerialPhonemeAnchorQuery:
    raw_q: str
    width: int
    constraint: Literal["final", "initial"]
    code_slots: list[tuple[int, str]]
    anchors: list[tuple[int, str]]
    mask: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.SERIAL_PHONEME


@dataclass(frozen=True)
class StarAnchorQuery:
    width: int
    constraint: str
    anchor: str
    anchor_pos: int
    code_slots: list[tuple[int, str]]
    code_prefix: Optional[str] = None

    @property
    def kind(self) -> QueryKind:
        return QueryKind.STAR_ANCHOR

    def to_handler_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WildcardCodeAnchorQuery:
    raw_q: str
    width: int
    slots: list[dict]
    head_literal: Optional[str] = None

    @property
    def kind(self) -> QueryKind:
        return QueryKind.WILDCARD_CODE_ANCHOR


@dataclass(frozen=True)
class CodeRefMiddleRhymeQuery:
    raw_q: str
    width: int
    anchor: str
    anchor_pos: int
    leading: str
    digits: str
    slots: list[dict]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.CODE_REF_MIDDLE_RHYME


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
    dual_phoneme: bool = False
    dual_initial_value: Optional[str] = None

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
    CompoundConnectSynQuery,
    CompoundConnectAntQuery,
    HybridTailEqualsAliasQuery,
    EqualsQuery,
    PrefixWildcardEqualsQuery,
    SerialPhonemeAnchorQuery,
    StarAnchorQuery,
    WildcardCodeAnchorQuery,
    CodeRefMiddleRhymeQuery,
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


def normalize_query(q: str) -> str:
    """查詢分派 lexer 入口：strip、code-tail、全形標點正規化。"""
    return normalize_search_query(q)


def normalize_and_parse(q: str) -> ParsedQuery:
    """正規化後分類查詢字串。無 DB access。"""
    return parse_query(normalize_query(q))


def parse_query(q: str) -> ParsedQuery:
    """Classify a normalized query string. No DB access."""
    relation_parsed = parse_relation_syntax(q)
    if relation_parsed:
        if relation_parsed["kind"] == "compound_connect_syn":
            return CompoundConnectSynQuery(
                code_prefix=relation_parsed.get("code_prefix"),
                connective=relation_parsed["connective"],
                rhyme_char=relation_parsed.get("rhyme_char"),
            )
        if relation_parsed["kind"] == "compound_connect_ant":
            return CompoundConnectAntQuery(
                code_prefix=relation_parsed.get("code_prefix"),
                connective=relation_parsed["connective"],
                rhyme_char=relation_parsed.get("rhyme_char"),
            )
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

    slot_hint = slot_connector_syntax_error(q)
    if slot_hint:
        return UnmatchedQuery(raw_q=q, hint=slot_hint)

    prefix_eq_hint = prefix_wildcard_equals_missing_eq_hint(q)
    if prefix_eq_hint:
        return UnmatchedQuery(raw_q=q, hint=prefix_eq_hint)

    pure_chars_hint = parse_pure_chars_serial_hint(q)
    if pure_chars_hint:
        return UnmatchedQuery(raw_q=q, hint=pure_chars_hint)

    prefix_eq = parse_prefix_wildcard_equals_query(q)
    if prefix_eq:
        return PrefixWildcardEqualsQuery(**prefix_eq)

    serial_parsed = parse_serial_phoneme_anchor_query(q)
    if serial_parsed:
        return SerialPhonemeAnchorQuery(**serial_parsed)

    if is_hybrid_tail_equals_alias(q):
        return HybridTailEqualsAliasQuery(raw_q=q, hybrid_q=hybrid_query_from_tail_equals(q))

    if is_framed_equals_query(q):
        return EqualsQuery(raw_q=q)

    from app.services.word_query_parser import mask_from_canonical_star_query

    mask_literal = mask_from_canonical_star_query(q)
    if mask_literal:
        return MaskQuery(raw_q=mask_literal)

    star_parsed = parse_star_anchor_query(q)
    if star_parsed:
        return StarAnchorQuery(**star_parsed)
    if "*" in q:
        if re.match(r"^\d+\*=([一-龥])\d+$", q):
            return UnmatchedQuery(
                raw_q=q,
                hint="`=` 只能緊貼錨字後面：請改用 `2*就3`（字面）或 `2*就=3`（同韻母）。",
            )
        if re.match(r"^\*[一-龥]\d+=$", q):
            return UnmatchedQuery(
                raw_q=q,
                hint="`=` 只能緊貼錨字後面：請改用 `*門0`（字面）或 `*門=0`（同韻母）。",
            )
        if re.match(r"^\*[一-龥](=)?$", q):
            return UnmatchedQuery(
                raw_q=q,
                hint="星號錨（頭格）需要右碼：請改用 `*門0`（字面）或 `*門=0`（同韻母）。",
            )

    at_tail_parsed = parse_at_tail_query(q)
    if at_tail_parsed:
        return LiteralRefQuery(**at_tail_parsed)

    contradiction_hint = parse_code_ref_rhyme_contradiction_hint(q)
    if contradiction_hint:
        return UnmatchedQuery(raw_q=q, hint=contradiction_hint)

    code_ref_middle = parse_code_ref_middle_rhyme_query(q)
    if code_ref_middle:
        return CodeRefMiddleRhymeQuery(**code_ref_middle)

    double_wild_rhyme = parse_double_wildcard_rhyme_query(q)
    if double_wild_rhyme:
        return RhymeAnchorQuery(**double_wild_rhyme)

    double_wild_initial = parse_double_wildcard_initial_query(q)
    if double_wild_initial:
        return RhymeAnchorQuery(**double_wild_initial)

    wca_parsed = parse_wildcard_code_anchor_query(q)
    if wca_parsed:
        return WildcardCodeAnchorQuery(**wca_parsed)

    triple_rhyme_parsed = parse_triple_rhyme_anchor_query(q)
    if triple_rhyme_parsed:
        return TripleRhymeAnchorQuery(**triple_rhyme_parsed)

    jyutping_anchor_parsed = parse_jyutping_anchor_query(q)
    if jyutping_anchor_parsed:
        if jyutping_anchor_parsed.get("dual_phoneme"):
            return JyutpingAnchorQuery(**jyutping_anchor_parsed)
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
            StarAnchorQuery,
            WildcardCodeAnchorQuery,
            CodeRefMiddleRhymeQuery,
            SerialPhonemeAnchorQuery,
            PrefixWildcardEqualsQuery,
            LiteralRefQuery,
        ),
    )


def uses_match_spec(parsed: Any) -> bool:
    """是否經 MatchSpec 進入缺字型查詢執行（含近義／反義複合，語法分類仍非缺字家族）。"""
    return is_mask_family_query(parsed) or isinstance(
        parsed,
        (
            CompoundSynQuery,
            CompoundAntQuery,
            CompoundConnectSynQuery,
            CompoundConnectAntQuery,
        ),
    )


VALID_FALLBACK_0243_MODES = frozenset({"m1", "m2"})


def resolve_fallback_0243_mode(fallback: str | None) -> str:
    """近反義前次0243搜尋模式 → 執行檔；缺省 0243模式。"""
    if fallback in VALID_FALLBACK_0243_MODES:
        return fallback
    return "m1"


def is_relation_syntax_query(q: str) -> bool:
    """是否為近反義關係查詢語法（觸發搜尋模式轉接）。"""
    parsed = normalize_and_parse(q)
    if isinstance(parsed, RelationLookupQuery):
        return True
    return isinstance(
        parsed,
        (
            CompoundSynQuery,
            CompoundAntQuery,
            CompoundConnectSynQuery,
            CompoundConnectAntQuery,
        ),
    )


def mode_redirect_hint(mode: str) -> str:
    """轉接提示文案（介面／API 保險一致）。"""
    label = "02493模式（緊）" if mode == "m2" else "0243模式（鬆）"
    return f"此語法已切換至 {label} 查詢"


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


def _apply_jyutping_anchor_code_slots(spec: "MatchSpec", parsed: JyutpingAnchorQuery) -> None:
    from app.services.position_match import SlotConstraint

    if parsed.code_slots:
        for pos, digit in parsed.code_slots:
            spec.slots.append(SlotConstraint(pos=pos, kind="code_digit", value=digit))
    elif parsed.code_prefix and parsed.width == len(parsed.code_prefix):
        for i, d in enumerate(parsed.code_prefix):
            spec.slots.append(SlotConstraint(pos=i, kind="code_digit", value=d))


def _build_jyutping_anchor_match_spec(parsed: JyutpingAnchorQuery) -> "MatchSpec":
    from app.services.position_match import MatchSpec, SlotConstraint

    spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_prefix)
    spec.mask = "?" * parsed.width
    spec.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind=parsed.anchor_kind,
            value=parsed.anchor_value,
        )
    )
    _apply_jyutping_anchor_code_slots(spec, parsed)
    return spec


def build_jyutping_dual_match_specs(parsed: JyutpingAnchorQuery) -> tuple["MatchSpec", "MatchSpec"]:
    """歧義粵拼錨 → 聲母維與韻母維 MatchSpec（ADR-0009）。"""
    from app.services.position_match import MatchSpec, SlotConstraint

    def _base() -> "MatchSpec":
        spec = MatchSpec(width=parsed.width, code_prefix=parsed.code_prefix)
        spec.mask = "?" * parsed.width
        _apply_jyutping_anchor_code_slots(spec, parsed)
        return spec

    initial = _base()
    initial.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind="initial_letters",
            value=(parsed.dual_initial_value or parsed.anchor_value),
        )
    )
    final = _base()
    final.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind="rhyme_letters",
            value=parsed.anchor_value,
        )
    )
    return initial, final


def normalize_to_match_spec(parsed: ParsedQuery) -> Optional["MatchSpec"]:
    """查詢分派：ParsedQuery → MatchSpec（含別名改寫）。無 DB。"""
    from app.services.query_match_spec_registry import build_match_spec_for_parsed

    parsed = _rewrite_mask_family_aliases(parsed)
    return build_match_spec_for_parsed(parsed)


def build_match_spec(parsed: ParsedQuery) -> Optional["MatchSpec"]:
    """Alias for normalize_to_match_spec（過渡期）。"""
    return normalize_to_match_spec(parsed)
