"""查詢分派型別 — QueryKind 與 ParsedQuery 家族（#4 自 query_parse 抽出）。"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal, Optional, Union

HYBRID_CODE_RE = re.compile(r"^(\d+)([一-龥]+)(\d*)$")

JYUTPING_ANCHOR_INVALID_HINT = (
    "粵拼錨無效：韻母片段喺收錄讀音中搵唔到對應。請檢查拼寫或改用漢字錨。"
)


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
    PARTIAL_RHYME_MASK = "partial_rhyme_mask"
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
class PartialRhymeMaskQuery:
    raw_q: str
    pattern: str
    width: int
    anchors: list[tuple[int, str]]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.PARTIAL_RHYME_MASK


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
    PartialRhymeMaskQuery,
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
