"""Position match core types (SlotConstraint, MatchSpec, CandidateSource)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Protocol, Union


ConstraintKind = Literal[
    "code_digit",        # 0243 碼數字約束（單一 digit）
    "literal_char",      # 必須完全匹配的粵字（canto char）
    "final_anchor",      # 韻母（final）錨點（參考字的發音）
    "initial_anchor",    # 聲母（initial）錨點
    "wildcard",          # 萬用字元（_ ? %），不做約束
]


@dataclass(frozen=True)
class SlotConstraint:
    """
    單一位置的約束條件。

    這是 PositionMatchEngine 的核心資料結構，取代原本散落在多處的
    code_digits、mask、anchor、literal_char 等參數。
    """
    pos: int                                   # 該約束在詞內的位置（0-based）
    kind: ConstraintKind
    value: Optional[Union[str, set[str]]] = None   # 視 kind 而定：digit 字串、canto char、phoneme set 等


@dataclass
class MatchSpec:
    """
    一次位置型查詢的完整規格。

    由 parser 產生的資料（CodeTailQuery、RhymeAnchorQuery、MaskQuery 等）
    轉換而成，或由 handle_* 薄層建構。
    """
    width: int                                 # 目標詞長度
    slots: list[SlotConstraint] = field(default_factory=list)

    # 額外全域約束
    code_prefix: Optional[str] = None          # 例如 code_tail 的 code_digits
    literal_priority: bool = False             # mask 類查詢常用（literal 數量優先排序）
    # 預留給 hybrid 等特殊語意
    hybrid_ref_chars: Optional[str] = None
    hybrid_ref_pos: Optional[int] = None

    # 為 mask 等
    mask: str = ""

    # 等號查詢／碼夾等號查詢（CONTEXT § 等號查詢、碼夾等號查詢）
    ref_literal: str = ""
    ref_start_pos: int = 0
    ref_dimension: Literal["initial", "final"] = "final"
    phoneme_anchor_only: bool = False
    whole_word_phoneme_match: bool = False

    # 未來可擴充的政策（排序、去重策略等）
    extra: dict[str, Any] = field(default_factory=dict)


class CandidateSource(Protocol):
    """
    候選來源抽象（隱藏 cache 與 DB 的差異）。

    實作會有兩種：
    - Cache 優先來源（word_cache + get_words_for_length）
    - DB 後援來源（GLOB + length_filter + apply_code_filter）

    回傳 (candidates, used_cache)：used_cache 為 True 時 candidates 是 dict list，否則是 ORM 物件 list。
    """

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        ...


@dataclass
class MaskFamilySearchResult:
    """缺字型查詢執行結果（供 query_dispatch 包成 SearchResult）。"""

    items: list
    cache_path: Optional[str] = None