"""
PositionMatchEngine（Phase 2.1 起步）

本模組為核准的 Phase 2 計畫（QueryEngine 深化 C1 + PositionMatchEngine 抽取／合併）第一步。

目標：
- 建立深層模組（deep module），集中處理所有「逐位置約束」邏輯（缺字、碼字、字面參考、韻錨、hybrid 等）。
- 定義核心抽象：SlotConstraint、MatchSpec、CandidateSource、PositionMatchEngine。
- 後續步驟會逐步把 mask_search.py 內的 filter_words_by_code_and_mask、get_length_candidates、matches_* 家族、build_*_options、hybrid 特殊處理等搬移進來。
- 維持與現有 handle_* 的行為 100% 一致（parse 優先順序、literal 優先、hybrid literal-or-phoneme 語意、快取命中 instant、所有 README §7 關鍵案例輸出與排序完全相同）。
- 最終讓 mask_search.py 的 handlers 變成薄層 adapter。

參考：
- 手交說明（Cursor Grok Build Handoff Note 2026-06-12）
- 架構審查報告 Candidate #2（Strong）
- 核准計畫：Phase 2.1 先抽取核心 engine，Phase 2.2 做 QueryEngine registry 內聚，Phase 2.3 視需要做正規化。
- README §7 Performance Rule 與 Enforcement 流程（每次實質變更都必須執行計時、結果比對、測試全綠、更新 WORKLOG）。
- CONTEXT.md「查詢分派」領域詞彙。

注意：
- 本階段僅建立骨架 + 抽象，不改變任何既有呼叫路徑與行為。
- 所有公開函式簽章在遷移期間保持相容。
- 技術識別項與類別名稱使用英文，文件與註解使用繁體中文。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Protocol, Sequence, Union

# Imports needed for the moved filter logic (kept minimal to avoid cycles)
from app.services.phoneme_lookup import final_options_for_char, initial_options_for_char
from app.services.word_query_parser import matches_mask_literal_chars
from app.services.word_serializer import get_word_parts, get_word_sort_code, get_word_text


# -----------------------------------------------------------------------------
# 核心抽象定義（直接對應現有程式碼中的概念）
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# PositionMatchEngine（核心引擎，目前為骨架）
# -----------------------------------------------------------------------------

class PositionMatchEngine:
    """
    集中處理所有位置型（mask / code-tail / rhyme-anchor / literal-ref / hybrid 等）查詢的 deep module。

    目前階段（Phase 2.1）：
    - 僅定義介面與骨架。
    - 後續會把 filter_words_by_code_and_mask、matches_*、get_length_candidates 等實作搬進來。
    - 會提供 apply(spec, source, db, mode) 主要入口。

    設計原則（來自核准計畫與架構報告）：
    - 單一深層模組擁有 SlotConstraint + MatchSpec。
    - 透過 CandidateSource 隔離快取／DB。
    - 維持 cache-first instant 路徑。
    - 所有行為與現有 mask_search 實作完全等價（由測試 + README §7 關鍵案例守護）。
    """

    def match(
        self,
        spec: MatchSpec,
        source: CandidateSource,
        db: Any,
        mode: str = "m1",
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Any]:
        """
        根據 MatchSpec 從來源取得候選並套用位置約束。

        目前為 stub，後續實作會：
        1. 呼叫 source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)
        2. 依 spec.slots 進行逐位置過濾（literal、code、phoneme anchor）
        3. 套用 literal_priority 等排序政策
        4. 回傳經過 serialize 前的候選列表（由呼叫者負責後續 serialize_page）
        """
        # Phase 2.1 骨架：尚未實作邏輯
        # 呼叫端（未來的 handle_* 薄層）仍會走舊程式碼，直到我們逐步遷移。
        raise NotImplementedError(
            "PositionMatchEngine.match 尚未實作（Phase 2.1 骨架階段）。"
            " 請先完成 helper 搬移與薄層更新，再啟用此入口。"
        )


# -----------------------------------------------------------------------------
# 便利建構函式（後續遷移時使用）
# -----------------------------------------------------------------------------

def build_match_spec_from_parsed(parsed: dict) -> MatchSpec:
    """
    從現有 parser 產生的 dict（或 ParsedQuery.to_handler_dict()）建構 MatchSpec。

    這是從舊 dict 世界過渡到新抽象的橋樑函式。
    實作會在 Phase 2.1 後續逐步補完。
    """
    # 骨架階段先回傳空 spec，實際轉換邏輯待 helper 搬移時補上
    width = parsed.get("width", 0) or 0
    return MatchSpec(width=width)


# 預留未來擴充的 registry 或 factory
# -----------------------------------------------------------------------------
# 純匹配工具（Phase 2.1 第一批搬移目標）
# 這些函式原本散落在 mask_search.py，現在集中到 PositionMatchEngine 負責的模組。
# -----------------------------------------------------------------------------

def matches_code_positions(code_str: str, required_codes: list[Optional[str]], mode: str) -> bool:
    """
    檢查詞的 0243 code 是否滿足每一個位置的 digit 約束。

    這是多個 handle（mask、code-tail、rhyme-anchor、at-tail）共用的核心比對。
    後續會擴充成更通用的 SlotConstraint 處理。
    """
    if len(code_str) != len(required_codes):
        return False
    for idx, req_digit in enumerate(required_codes):
        if req_digit is None:
            continue
        # 延遲 import 避免循環（utils 會被很多地方依賴）
        from utils import get_code_variants
        if code_str[idx] not in set(get_code_variants(req_digit, mode)):
            return False
    return True


def matches_phoneme_at_position(
    word,
    pos: int,
    anchor: str,
    *,
    constraint: str,
    db,
) -> bool:
    """
    檢查指定位置的聲母或韻母是否符合參考字的發音選項。

    原位於 mask_search.py，僅供 filter_words_by_code_and_mask 使用。
    """
    if constraint == "final":
        options = final_options_for_char(anchor, db)
        parts = get_word_parts(word, "finals")
    else:
        options = initial_options_for_char(anchor, db)
        parts = get_word_parts(word, "initials")
    if not options or pos >= len(parts):
        return False
    return parts[pos] in options


def filter_words_by_code_and_mask(
    candidates: list,
    *,
    width: int,
    code_digits: str,
    mode: str,
    mask: str,
    db,
    anchor_pos: Optional[int] = None,
    anchor: Optional[str] = None,
    constraint: Optional[str] = None,
    literal_char: Optional[str] = None,
) -> list:
    """
    核心位置過濾器：同時套用長度、mask literal、特定 code 數字、以及可選的 phoneme anchor / literal_char 約束。

    這是 Phase 2.1 重點搬移的函式，原為 mask_search.py 內多個 handle_*（rhyme_anchor, code_tail, at_tail）的共用實作。
    行為必須與原版 100% 一致（由後續 enforcement 驗證）。
    """
    required_codes: list[Optional[str]] = [None] * width
    if code_digits:
        for i, d in enumerate(code_digits):
            required_codes[i] = d

    filtered = []
    for word in candidates:
        word_char = get_word_text(word)
        if len(word_char) != width:
            continue
        if mask and not matches_mask_literal_chars(word_char, mask):
            continue
        if literal_char is not None and word_char[-1] != literal_char:
            continue
        word_code_str = get_word_sort_code(word)
        word_finals = get_word_parts(word, "finals")
        if not word_code_str or not word_finals:
            continue
        if not matches_code_positions(word_code_str, required_codes, mode):
            continue
        if anchor_pos is not None and anchor and constraint:
            if not matches_phoneme_at_position(
                word, anchor_pos, anchor, constraint=constraint, db=db,
            ):
                continue
        filtered.append(word)
    return filtered


__all__ = [
    "SlotConstraint",
    "MatchSpec",
    "CandidateSource",
    "PositionMatchEngine",
    "build_match_spec_from_parsed",
    "matches_code_positions",
    "matches_phoneme_at_position",
    "filter_words_by_code_and_mask",
]