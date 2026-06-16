"""PositionMatchEngine, filters, and query execution entry points."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from app.domain.lexicon.reference_reading import (
    anchor_phoneme_options,
    equals_authoritative_row,
)
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.models.word import Word
from app.services.essay_sort import default_word_sort_key
from app.services.position_match.sources import (
    _resolve_mask_family_source,
    get_candidates_for_length,
)
from app.services.position_match.spec import (
    CandidateSource,
    MaskFamilySearchResult,
    MatchSpec,
    SlotConstraint,
)
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_query_parser import matches_mask_literal_chars
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import (
    get_words_for_length,
    is_word_cache_ready,
    narrow_candidates_by_phoneme_anchor,
)


class PositionMatchEngine:
    """
    集中處理所有位置型（mask / code-tail / rhyme-anchor / literal-ref / hybrid 等）查詢的 deep module。
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
        """
        if pre_candidates is not None:
            candidates = pre_candidates
        elif source is None:
            candidates, _ = get_candidates_for_length(db, spec.width, code=spec.code_prefix, mode=mode)
        else:
            candidates, _ = source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)

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
                word_finals = get_rhyme_finals(word)
                word_char = get_word_text(word)
                if matches_hybrid_ref_chars(
                    word_char, word_finals, spec.hybrid_ref_chars, spec.hybrid_ref_pos, target_final_options
                ):
                    filtered.append(word)
            return filtered

        return filter_candidates_by_match_spec(candidates, spec, mode, db)

    def _match_equals_whole_word(
        self,
        spec: MatchSpec,
        db: Any,
        mode: str,
        *,
        target: Any,
        target_parts: list,
        is_final: bool,
    ) -> list[Any]:
        """整詞同韻／同聲：cache 長度桶優先；DB 以 finals/initials 欄預篩再驗證。"""
        full_code = spec.code_prefix or ""
        target_key = tuple(target_parts)
        cached = _equals_length_bucket_candidates(spec.width, full_code or None, mode)
        storage_field = "finals" if is_final else "initials"
        target_storage_key = _phoneme_storage_key(target, storage_field)

        if cached is not None:
            pool = cached
            if target_storage_key:
                pool = [
                    w
                    for w in pool
                    if _phoneme_storage_key(w, storage_field) == target_storage_key
                ]
            if is_final:
                return [w for w in pool if tuple(get_rhyme_finals(w)) == target_key]
            return [w for w in pool if tuple(get_word_parts(w, "initials")) == target_key]

        query = db.query(Word).filter(length_filter(spec.width))
        if full_code:
            query = apply_code_filter(query, full_code, mode)
        if is_final:
            db_literal = _phoneme_db_literal(target, "finals")
            if db_literal:
                query = query.filter(Word.finals == db_literal)
            return [
                w
                for w in query.all()
                if tuple(get_rhyme_finals(w)) == target_key
            ]
        db_literal = _phoneme_db_literal(target, "initials")
        if db_literal:
            query = query.filter(Word.initials == db_literal)
        return query.all()

    def match_equals(self, spec: MatchSpec, db: Any, mode: str = "m1") -> list[Any]:
        """等號查詢／碼夾等號查詢：參考字讀音經 reference_reading 解析。"""
        from app.utils.json_helpers import load_json_list

        if not spec.ref_literal:
            return []

        target = equals_authoritative_row(spec.ref_literal, db, allow_inject=True)
        if not target:
            return []

        is_final = spec.ref_dimension == "final"
        target_parts = (
            get_rhyme_finals(target)
            if is_final
            else load_json_list(target.initials)
        )
        full_code = spec.code_prefix or ""

        query = db.query(Word)
        query = apply_code_filter(query, full_code, mode)
        query = query.filter(length_filter(spec.width))

        if spec.whole_word_phoneme_match:
            return self._match_equals_whole_word(
                spec,
                db,
                mode,
                target=target,
                target_parts=target_parts,
                is_final=is_final,
            )

        candidates = query.limit(2000).all()
        return [
            word
            for word in candidates
            if matches_equals_phoneme_span(
                word,
                target_parts,
                spec.ref_start_pos,
                phoneme_anchor_only=spec.phoneme_anchor_only,
                ref_literal=spec.ref_literal,
                dimension=spec.ref_dimension,
            )
        ]


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
    items, _ = run_position_query_tracked(
        spec,
        db,
        mode,
        limit,
        offset,
        source=source,
        pre_candidates=pre_candidates,
        sort_key=sort_key,
    )
    return items


def run_position_query_tracked(
    spec: MatchSpec,
    db: Any,
    mode: str,
    limit: int,
    offset: int,
    *,
    source: CandidateSource | None = None,
    pre_candidates: list[Any] | None = None,
    sort_key: Callable[[Any], Any] | None = None,
) -> tuple[list, bool]:
    """Like run_position_query; also returns whether candidates came from word_cache."""
    from app.services.word_serializer import serialize_page

    from_cache = False
    if pre_candidates is not None:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=pre_candidates)
    elif source is not None:
        candidates, from_cache = source.get_candidates(spec.width, code=spec.code_prefix, mode=mode)
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode, pre_candidates=candidates)
    else:
        filtered = _DEFAULT_ENGINE.match(spec, None, db, mode)

    key = sort_key or default_word_sort_key
    filtered.sort(key=key)
    return serialize_page(filtered, offset, limit), from_cache


def _word_stored_phoneme_json(word: Any, field: str):
    if isinstance(word, dict):
        return word.get(field)
    return getattr(word, field, None)


def _phoneme_storage_key(word: Any, field: str) -> tuple:
    """Normalize stored finals/initials (JSON str or list) for equality prefilter."""
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, list):
        return tuple(raw)
    if isinstance(raw, str) and raw:
        from app.utils.json_helpers import load_json_list

        return tuple(load_json_list(raw))
    return ()


def _phoneme_db_literal(word: Any, field: str) -> str:
    """DB column literal for SQL filter (ORM JSON string)."""
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return json.dumps(raw, ensure_ascii=False, separators=(", ", ": "))
    return ""


def _equals_length_bucket_candidates(
    width: int,
    code_prefix: Optional[str],
    mode: str,
) -> Optional[list]:
    """word_cache 長度桶候選；未就緒時回傳 None 走 DB。"""
    if not is_word_cache_ready():
        return None
    candidates = get_words_for_length(width)
    if not code_prefix:
        return candidates
    variants = set(get_code_variants(code_prefix, mode))
    return [w for w in candidates if get_word_sort_code(w) in variants]


def run_equals_query(q: str, db: Any, mode: str, limit: int, offset: int) -> list:
    """等號查詢統一入口：spec 建構 → engine → 排序 → 序列化。"""
    from app.services.essay_sort import sort_words
    from app.services.query_parse import build_equals_match_spec
    from app.services.word_serializer import deduplicate_words, serialize_page

    spec = build_equals_match_spec(q)
    if spec is None:
        return []
    filtered = _DEFAULT_ENGINE.match_equals(spec, db, mode)
    return serialize_page(sort_words(deduplicate_words(filtered)), offset, limit)


def execute_match_spec(
    spec: MatchSpec,
    *,
    code: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    db: Any,
) -> MaskFamilySearchResult:
    """缺字型查詢執行：僅收 MatchSpec（CONTEXT § 缺字型查詢執行）。"""
    if spec is None or spec.width == 0:
        return MaskFamilySearchResult(items=[])

    source, sort_key = _resolve_mask_family_source(spec, db, mode, code)
    if source is None:
        return MaskFamilySearchResult(items=[])

    items, from_cache = run_position_query_tracked(
        spec, db, mode, limit, offset, source=source, sort_key=sort_key
    )
    return MaskFamilySearchResult(
        items=items,
        cache_path="ready" if from_cache else "fallback",
    )


def matches_equals_phoneme_span(
    word,
    ref_parts: list,
    start_pos: int,
    *,
    phoneme_anchor_only: bool,
    ref_literal: str,
    dimension: str,
) -> bool:
    """碼夾等號 span：參考詞 JSON 逐格精確比對（非 options OR）。"""
    char_text = get_word_text(word)
    if not phoneme_anchor_only and ref_literal and ref_literal not in char_text:
        return False
    field = "finals" if dimension == "final" else "initials"
    word_parts = get_rhyme_finals(word) if dimension == "final" else get_word_parts(word, field)
    if not word_parts:
        return False
    for i in range(len(ref_parts)):
        pos = start_pos + i
        if pos < len(word_parts) and i < len(ref_parts):
            if ref_parts[i] and ref_parts[i] != word_parts[pos]:
                return False
    return True


def matches_code_positions(code_str: str, required_codes: list[Optional[str]], mode: str) -> bool:
    """檢查詞的 0243 code 是否滿足每一個位置的 digit 約束。"""
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
    """檢查指定位置的聲母或韻母是否符合參考字的發音選項。"""
    if constraint == "final":
        options = anchor_phoneme_options(anchor, "final", db, allow_inject=True)
        parts = get_rhyme_finals(word)
    else:
        options = anchor_phoneme_options(anchor, "initial", db, allow_inject=True)
        parts = get_word_parts(word, "initials")
    if not options or pos >= len(parts):
        return False
    return parts[pos] in options


def _slot_constraint_matches(word, slot, db) -> bool:
    from app.services.jyutping_anchor_match import matches_jyutping_anchor_at_position

    if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
        return matches_jyutping_anchor_at_position(
            word, slot.pos, slot.kind, str(slot.value or ""), db
        )
    return False


def _group_candidates_by_char(candidates: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for word in candidates:
        char = get_word_text(word)
        grouped.setdefault(char, []).append(word)
    return grouped


def preferred_pronunciation_rows(rows: list) -> list:
    """多音字：僅保留 pron_rank 最佳（預設讀音）的候選列。"""
    if not rows:
        return []
    ranked = [
        (pron_rank_sort_value_for_word(get_word_text(word), get_word_jyutping(word)), word)
        for word in rows
    ]
    best = min(rank for rank, _ in ranked)
    return [word for rank, word in ranked if rank == best]


def _word_passes_position_filters(
    word,
    *,
    width: int,
    required_codes: list[Optional[str]],
    mode: str,
    mask: str,
    db,
    anchor_pos: Optional[int],
    anchor: Optional[str],
    constraint: Optional[str],
    literal_char: Optional[str],
    slots: Optional[list] = None,
) -> bool:
    word_char = get_word_text(word)
    if len(word_char) != width:
        return False
    if mask and not matches_mask_literal_chars(word_char, mask):
        return False
    if literal_char is not None and word_char[-1] != literal_char:
        return False
    word_code_str = get_word_sort_code(word)
    word_finals = get_rhyme_finals(word)
    if not word_code_str or not word_finals:
        return False
    if any(req is not None for req in required_codes):
        if not matches_code_positions(word_code_str, required_codes, mode):
            return False
    if anchor_pos is not None and anchor and constraint:
        if not matches_phoneme_at_position(
            word, anchor_pos, anchor, constraint=constraint, db=db,
        ):
            return False
    for slot in slots or []:
        if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
            if not _slot_constraint_matches(word, slot, db):
                return False
    return True


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
    slots: Optional[list] = None,
) -> list:
    """核心位置過濾器：同時套用長度、mask literal、特定 code 數字、以及可選的 phoneme anchor / literal_char 約束。"""
    required_codes: list[Optional[str]] = [None] * width
    if code_digits:
        for i, d in enumerate(code_digits):
            required_codes[i] = d

    if mask:
        for i, ch in enumerate(mask):
            if i < width and ch.isdigit():
                required_codes[i] = ch

    if slots:
        for slot in slots:
            if getattr(slot, 'kind', None) == "code_digit" and slot.pos < width and slot.value is not None:
                required_codes[slot.pos] = str(slot.value)

    filtered = []
    has_code_digit_constraints = any(req is not None for req in required_codes)
    if has_code_digit_constraints:
        for _char, group in _group_candidates_by_char(candidates).items():
            for word in preferred_pronunciation_rows(group):
                if _word_passes_position_filters(
                    word,
                    width=width,
                    required_codes=required_codes,
                    mode=mode,
                    mask=mask,
                    db=db,
                    anchor_pos=anchor_pos,
                    anchor=anchor,
                    constraint=constraint,
                    literal_char=literal_char,
                    slots=slots,
                ):
                    filtered.append(word)
                    break
    else:
        for word in candidates:
            if _word_passes_position_filters(
                word,
                width=width,
                required_codes=required_codes,
                mode=mode,
                mask=mask,
                db=db,
                anchor_pos=anchor_pos,
                anchor=anchor,
                constraint=constraint,
                literal_char=literal_char,
                slots=slots,
            ):
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
    if anchor_pos is not None and anchor and constraint:
        candidates = narrow_candidates_by_phoneme_anchor(
            candidates, spec.width, anchor_pos, anchor, constraint, db,
        )
    for slot in spec.slots:
        if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
            candidates = [
                w for w in candidates
                if _slot_constraint_matches(w, slot, db)
            ]
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
            options = anchor_phoneme_options(ch, "final", db, allow_inject=True)
            if options:
                target_final_options[pos] = options
    return target_final_options


def word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    """檢查詞的最後一個音節的 final 是否在允許選項中。"""
    if not final_options:
        return True
    word_finals = get_rhyme_finals(word)
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