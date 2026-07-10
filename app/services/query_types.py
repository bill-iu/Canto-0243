"""查詢分派型別 — QueryKind 與 ParsedQuery 家族（#4 自 query_parse 抽出）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Optional, Union

from app.services._generated.query_kind_registry import QueryKind

JYUTPING_ANCHOR_INVALID_HINT = (
    "粵拼錨無效：韻母片段喺收錄讀音中搵唔到對應。請檢查拼寫或改用漢字錨。"
)

# QueryKind SSOT: contracts/query-kind-manifest.json → codegen (ADR-0035)


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
class CompoundDoubledSyllableQuery:
    width: int
    code_prefix: Optional[str]
    rhyme_char: Optional[str]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.COMPOUND_DOUBLED_SYLLABLE


@dataclass(frozen=True)
class HeteronymCodeQuery:
    left_template: str
    right_template: str
    width: int

    @property
    def kind(self) -> QueryKind:
        return QueryKind.HETERONYM_CODE


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
class PartialInitialMaskQuery:
    raw_q: str
    pattern: str
    width: int
    anchors: list[tuple[int, str]]

    @property
    def kind(self) -> QueryKind:
        return QueryKind.PARTIAL_INITIAL_MASK


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
class PlusAnchorQuery:
    width: int
    constraint: str
    anchor: str
    anchor_pos: int
    code_slots: list[tuple[int, str]]
    code_prefix: Optional[str] = None

    @property
    def kind(self) -> QueryKind:
        return QueryKind.PLUS_ANCHOR

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
class MaskQuery:
    raw_q: str

    @property
    def kind(self) -> QueryKind:
        return QueryKind.MASK


@dataclass(frozen=True)
class PingZeSerialQuery:
    raw_q: str
    pzmode: Literal["m1", "m2", "m3"] = "m1"
    anchor: Optional[str] = None

    @property
    def kind(self) -> QueryKind:
        return QueryKind.PING_ZE_SERIAL


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
    CompoundDoubledSyllableQuery,
    HeteronymCodeQuery,
    CompoundAntQuery,
    CompoundConnectSynQuery,
    CompoundConnectAntQuery,
    EqualsQuery,
    PrefixWildcardEqualsQuery,
    PartialRhymeMaskQuery,
    PartialInitialMaskQuery,
    SerialPhonemeAnchorQuery,
    PlusAnchorQuery,
    WildcardCodeAnchorQuery,
    CodeRefMiddleRhymeQuery,
    LiteralRefQuery,
    RhymeAnchorQuery,
    TripleRhymeAnchorQuery,
    JyutpingAnchorQuery,
    MaskQuery,
    PingZeSerialQuery,
    DigitCodeQuery,
    WordLookupQuery,
    JyutpingFragmentQuery,
    UnmatchedQuery,
]
