"""
PositionMatchEngine（Phase 2.1 起步）

本模組為核准的 Phase 2 計畫（QueryEngine 深化 C1 + PositionMatchEngine 抽取／合併）第一步。

目標：
- 建立深層模組（deep module），集中處理所有「逐位置約束」邏輯（缺字、碼字、字面參考、韻錨、hybrid 等）。
- 定義核心抽象：SlotConstraint、MatchSpec、CandidateSource、PositionMatchEngine。
- 後續步驟會逐步把 filter、matches_* 家族、build_*_options、hybrid 特殊處理等集中於本模組。
- 維持與既有 handle_* 的行為 100% 一致（parse 優先順序、literal 優先、hybrid literal-or-phoneme 語意、快取命中 instant、所有 README §7 關鍵案例輸出與排序完全相同）。
- QueryEngine registry 直接呼叫 run_position_query（P-A：mask_search 已刪除）。

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
from app.services.word_serializer import get_word_parts, get_word_sort_code, get_word_text, get_word_jyutping
from app.services.essay_sort import default_word_sort_key
from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.curated_index import curated_sort_boost
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word

# For candidate acquisition (moved from mask_search)
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import get_words_for_length
from app.services.word_db_filters import apply_code_filter, length_filter

# Needed by the moved candidate helpers
from app.models.word import Word


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

    # 為 mask 等
    mask: str = ""

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
class LengthMaskCandidateSource:
    """Cache-first 長度桶 + mask literal 預過濾（韻錨／碼字 tail／字面參考）。"""

    db: Any
    mask: str

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        return get_length_candidates(self.db, length, self.mask)


@dataclass
class LengthCodeCandidateSource:
    """Cache-first 長度桶 + 可選 0243 碼過濾（hybrid 等）。"""

    db: Any
    code: Optional[str] = None
    mode: str = "m1"
    fallback_limit: int = 2000

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        effective_code = code if code is not None else self.code
        effective_mode = mode or self.mode
        return get_candidates_for_length(
            self.db,
            length,
            code=effective_code,
            mode=effective_mode,
            fallback_limit=self.fallback_limit,
        )


@dataclass
class MaskWildcardCandidateSource:
    """缺字查詢：cache literal 預過濾或 DB GLOB + 可選 code filter。"""

    db: Any
    mask: str
    mode: str = "m1"
    query_code: Optional[str] = None

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        from app.services.word_query_parser import mask_char_glob_pattern, parse_mask_query

        effective_mode = mode or self.mode
        effective_code = code if code is not None else self.query_code
        _, required_codes, _ = parse_mask_query(self.mask)

        candidates = get_words_for_length(length)
        if candidates:
            return [
                w for w in candidates
                if matches_mask_literal_chars(get_word_text(w), self.mask)
            ], True

        glob_pat = mask_char_glob_pattern(self.mask)
        query = self.db.query(Word).filter(
            length_filter(length),
            Word.char.op("GLOB")(glob_pat),
        )
        code_filter = "".join(required_codes) if all(req is not None for req in required_codes) else None
        if code_filter:
            query = apply_code_filter(query, code_filter, effective_mode)
        elif effective_code:
            query = apply_code_filter(query, effective_code, effective_mode)
        return query.order_by(Word.char, Word.jyutping).all(), False


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
        pre_candidates: Optional[list] = None,
    ) -> list[Any]:
        """
        根據 MatchSpec 從來源取得候選並套用位置約束。

        使用已搬移的 helpers 實作基本過濾。
        支援當前 thin handlers 使用的 spec 欄位。
        """
        if pre_candidates is not None:
            candidates = pre_candidates
        elif source is None:
            candidates, _ = get_candidates_for_length(db, spec.width, code=spec.code_prefix, mode=mode)
        else:
            candidates, _ = source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)

        # Hybrid special case (centralized matching using migrated helper)
        if spec.hybrid_ref_chars is not None and spec.hybrid_ref_pos is not None:
            target_final_options = build_final_options_at_positions(
                spec.hybrid_ref_chars, spec.hybrid_ref_pos, spec.width, db
            )
            filtered = []
            allowed_full_codes = set(get_code_variants(spec.code_prefix or "", mode)) if spec.code_prefix else set()
            for word in candidates:
                word_code_str = get_word_sort_code(word)
                if spec.code_prefix and word_code_str not in allowed_full_codes:
                    continue
                word_finals = get_word_parts(word, "finals")
                word_char = get_word_text(word)
                if matches_hybrid_ref_chars(
                    word_char, word_finals, spec.hybrid_ref_chars, spec.hybrid_ref_pos, target_final_options
                ):
                    filtered.append(word)
            return filtered

        # Standard path: apply MatchSpec slot constraints via deep filter
        return filter_candidates_by_match_spec(candidates, spec, mode, db)


_DEFAULT_ENGINE = PositionMatchEngine()


def run_position_query(
    spec: MatchSpec,
    db: Any,
    mode: str,
    limit: int,
    offset: int,
    *,
    source: CandidateSource | None = None,
    pre_candidates: list[Any] | None = None,
    sort_key: Callable[[Any], Any] | None = None,
) -> list:
    """Phase 2.4：位置型查詢統一入口（engine + sort + serialize）。"""
    from app.services.word_serializer import serialize_page

    if pre_candidates is not None:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=pre_candidates)
    elif source is not None:
        filtered = _DEFAULT_ENGINE.match(spec, source, db, mode)
    else:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode)

    key = sort_key or default_word_sort_key
    filtered.sort(key=key)
    return serialize_page(filtered, offset, limit)


# -----------------------------------------------------------------------------
# 便利建構函式（後續遷移時使用）
# -----------------------------------------------------------------------------

def build_match_spec_from_parsed(parsed: dict) -> MatchSpec:
    """
    從現有 parser 產生的 dict（或 ParsedQuery.to_handler_dict()）建構 MatchSpec。

    這是從舊 dict 世界過渡到新抽象的橋樑函式。
    目前支援 rhyme_anchor / code_tail / at_tail 等常見位置型 parsed。
    """
    width = parsed.get("width", 0) or 0
    spec = MatchSpec(width=width)

    # 設定全域 code_prefix 如果有
    if "code_digits" in parsed and parsed["code_digits"]:
        spec.code_prefix = parsed["code_digits"]

    # rhyme anchor / 參考字錨點
    if "anchor_pos" in parsed and "anchor" in parsed and "constraint" in parsed:
        kind = "final_anchor" if parsed["constraint"] == "final" else "initial_anchor"
        spec.slots.append(SlotConstraint(
            pos=parsed["anchor_pos"],
            kind=kind,
            value=parsed["anchor"]
        ))

    # literal char (e.g. at_tail)
    if "literal_char" in parsed and parsed["literal_char"]:
        # 對於 at_tail，通常是尾部 literal
        # 這裡簡化為在對應位置加 literal_char 約束（實際由 handler 計算位置）
        # 為了相容，先不加，留給後續完整實作
        pass

    # 其他如 mask literal 會在後續 MatchSpec 擴充中處理
    # 目前先支援 anchor 類，確保 handler 能開始使用 spec

    return spec


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
    slots: Optional[list] = None,  # Phase 2 support for code_digit slots (e.g. from mask normalization)
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

    # Support code digits embedded in the mask itself (e.g. "門0" means pos0 literal "門" + pos1 code_digit "0";
    # "好23" etc.). These are code constraints, not char literals (handled separately by matches_mask_literal_chars).
    # This fixes inaccurate results for mixed literal+digit masks.
    if mask:
        for i, ch in enumerate(mask):
            if i < width and ch.isdigit():
                required_codes[i] = ch

    # Also honor explicit code_digit slots (populated e.g. by mask handler for "門0" style;
    # this makes the SlotConstraint model drive code constraints too).
    if slots:
        for slot in slots:
            if getattr(slot, 'kind', None) == "code_digit" and slot.pos < width and slot.value is not None:
                required_codes[slot.pos] = str(slot.value)

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


def filter_candidates_by_match_spec(
    candidates: list,
    spec: MatchSpec,
    mode: str,
    db,
) -> list:
    """Apply MatchSpec (slots + mask + code_prefix) to candidate 詞條 rows."""
    anchor_pos: Optional[int] = None
    anchor: Optional[str] = None
    constraint: Optional[str] = None
    literal_char: Optional[str] = None
    for slot in spec.slots:
        if slot.kind == "literal_char" and slot.pos == spec.width - 1:
            literal_char = slot.value
        elif slot.kind in ("final_anchor", "initial_anchor"):
            anchor_pos = slot.pos
            anchor = slot.value
            constraint = "final" if slot.kind == "final_anchor" else "initial"
    return filter_words_by_code_and_mask(
        candidates,
        width=spec.width,
        code_digits=spec.code_prefix or "",
        mode=mode,
        mask=spec.mask or "",
        db=db,
        anchor_pos=anchor_pos,
        anchor=anchor,
        constraint=constraint,
        literal_char=literal_char,
        slots=spec.slots,
    )


__all__ = [
    "SlotConstraint",
    "MatchSpec",
    "CandidateSource",
    "LengthMaskCandidateSource",
    "LengthCodeCandidateSource",
    "MaskWildcardCandidateSource",
    "run_position_query",
    "PositionMatchEngine",
    "build_match_spec_from_parsed",
    "matches_code_positions",
    "matches_phoneme_at_position",
    "filter_words_by_code_and_mask",
    "filter_candidates_by_match_spec",
    "get_length_candidates",
    "get_candidates_for_length",
    "build_final_options_at_positions",
    "word_matches_last_final",
    "matches_final_options",
    "matches_hybrid_ref_chars",
    "mask_priority_key",
]


# -----------------------------------------------------------------------------
# 候選取得工具（Phase 2.1 繼續搬移）
# 原本散落在 mask_search.py，現在集中管理。
# 保留原有行為（cache-first + DB fallback）。
# -----------------------------------------------------------------------------

def get_length_candidates(db, width: int, mask: str):
    """
    取得指定長度的候選詞，並對 cache 命中者先做 mask literal 預過濾。
    用於 rhyme-anchor、code-tail、at-tail 等需要 mask 的情境。
    """
    candidates = get_words_for_length(width)
    if candidates:
        return [w for w in candidates if matches_mask_literal_chars(get_word_text(w), mask)], True
    # 延遲 import 避免循環
    from app.services.word_query_parser import mask_char_glob_pattern as _mask_glob
    glob_pat = _mask_glob(mask)
    query = db.query(Word).filter(
        length_filter(width),
        Word.char.op("GLOB")(glob_pat),
    )
    return query.order_by(Word.char, Word.jyutping).all(), False


def get_candidates_for_length(
    db: Any,
    length: int,
    *,
    code: Optional[str] = None,
    mode: str = "m1",
    fallback_limit: int = 2000,
):
    """
    通用長度候選取得（無 mask 預過濾）。
    用於 hybrid 等情境。
    """
    candidates = get_words_for_length(length)
    if candidates:
        return candidates, True
    query = db.query(Word).filter(length_filter(length))
    if code:
        query = apply_code_filter(query, code, mode)
    return query.order_by(Word.char, Word.jyutping).limit(fallback_limit).all(), False


# -----------------------------------------------------------------------------
# 其餘位置匹配核心 helper（Phase 2.1 繼續搬移）
# 從 mask_search.py 抽取，集中管理，行為完全等價。
# 後續將用於 PositionMatchEngine 內部實作。
# -----------------------------------------------------------------------------

def build_final_options_at_positions(
    ref_chars: str,
    start_pos: int,
    width: int,
    db,
) -> list[Optional[set[str]]]:
    """為參考字串的每個位置建立可能的 final 選項集合。"""
    target_final_options: list[Optional[set[str]]] = [None] * width
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if 0 <= pos < width:
            options = final_options_for_char(ch, db)
            if options:
                target_final_options[pos] = options
    return target_final_options


def word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    """檢查詞的最後一個音節的 final 是否在允許選項中。"""
    if not final_options:
        return True
    word_finals = get_word_parts(word, "finals")
    return len(word_finals) >= 2 and word_finals[-1] in final_options


def matches_final_options(word_finals: list, target_final_options: list[Optional[set[str]]]) -> bool:
    """檢查詞的 finals list 是否滿足所有位置的 target options。"""
    if len(word_finals) != len(target_final_options):
        return False
    for idx, options in enumerate(target_final_options):
        if not options:
            continue
        if idx >= len(word_finals) or word_finals[idx] not in options:
            return False
    return True


def matches_hybrid_ref_chars(
    word_char: str,
    word_finals: list,
    ref_chars: str,
    start_pos: int,
    target_final_options: list[Optional[set[str]]],
) -> bool:
    """Rhyme match at ref positions, or literal match (so 23就 includes 23@就 results)."""
    width = len(target_final_options)
    if len(word_char) != width or len(word_finals) != width:
        return False
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if pos < 0 or pos >= width:
            return False
        if word_char[pos] == ch:
            continue
        options = target_final_options[pos]
        if options and word_finals[pos] in options:
            continue
        return False
    return True


def mask_priority_key(word, literal_positions: list[tuple[int, str]]):
    """literal 數 > curated > essay > pron_rank > char/jyut。"""
    char = get_word_text(word)
    jyutping = get_word_jyutping(word)
    exact_count = sum(1 for pos, ch in literal_positions if pos < len(char) and char[pos] == ch)
    return (
        -exact_count,
        -curated_sort_boost(char),
        -get_essay_frequency(char),
        pron_rank_sort_value_for_word(char, jyutping),
        char,
        jyutping,
    )
