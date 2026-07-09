"""MF-5 F1 — code_digit / mask literal / position filter orchestration."""
from __future__ import annotations

from typing import Optional

from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.services.position_match.filters.f2_phoneme_anchor import matches_phoneme_at_position
from app.services.position_match.filters.f3_letters import slot_constraint_matches
from app.services.position_match.mask_adapter import matches_mask_literal_chars
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_jyutping,
    get_word_sort_code,
    get_word_text,
)
from app.utils.jyutping_codec import get_code_variants

def matches_code_positions(code_str: str, required_codes: list[Optional[str]], mode: str) -> bool:
    """逐格 digit 鬆檔比對。required 可短於 code（前綴）；None 格跳過。"""
    if not required_codes:
        return True
    if not code_str and any(r is not None for r in required_codes):
        return False
    for idx, req_digit in enumerate(required_codes):
        if req_digit is None:
            continue
        if idx >= len(code_str):
            return False
        if code_str[idx] not in set(get_code_variants(str(req_digit), mode)):
            return False
    return True

def _group_candidates_by_char(candidates: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for word in candidates:
        char = get_word_text(word)
        grouped.setdefault(char, []).append(word)
    return grouped


def preferred_pronunciation_rows(rows: list) -> list:
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
    anchor_slots = [s for s in (slots or []) if s.kind in ("final_anchor", "initial_anchor")]
    if anchor_slots:
        for slot in anchor_slots:
            constraint = "final" if slot.kind == "final_anchor" else "initial"
            if not matches_phoneme_at_position(
                word, slot.pos, slot.value, constraint=constraint, db=db,
            ):
                return False
    elif anchor_pos is not None and anchor and constraint:
        if not matches_phoneme_at_position(
            word, anchor_pos, anchor, constraint=constraint, db=db,
        ):
            return False
    for slot in slots or []:
        if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
            if not slot_constraint_matches(word, slot, db):
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
    required_codes: Optional[list] = None,
) -> list:
    # PR-A: prefer explicit required_codes (slots/mask); ignore legacy code_digits blob
    if required_codes is None:
        required_codes = [None] * width
        if mask:
            for i, ch in enumerate(mask):
                if i < width and ch.isdigit():
                    required_codes[i] = ch
        if slots:
            for slot in slots:
                if getattr(slot, "kind", None) == "code_digit" and slot.pos < width and slot.value is not None:
                    required_codes[slot.pos] = str(slot.value)
        # legacy: only if no slot/mask digits at all (callers should pass required_codes)
        if code_digits and not any(r is not None for r in required_codes):
            for i, d in enumerate(code_digits):
                if i < width and str(d).isdigit():
                    required_codes[i] = str(d)

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
