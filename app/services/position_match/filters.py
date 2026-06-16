"""缺字型查詢執行 — 候選比對與 slot 過濾。"""

from __future__ import annotations

from typing import Any, Optional

from app.domain.lexicon.reference_reading import anchor_phoneme_options
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.services.position_match.spec import MatchSpec
from app.services.word_query_parser import matches_mask_literal_chars
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import narrow_candidates_by_phoneme_anchor


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
    if constraint == "final":
        options = anchor_phoneme_options(anchor, "final", db, allow_inject=True)
        parts = get_rhyme_finals(word)
    else:
        options = anchor_phoneme_options(anchor, "initial", db, allow_inject=True)
        parts = get_word_parts(word, "initials")
    if not options or pos >= len(parts):
        return False
    return parts[pos] in options


def slot_constraint_matches(word, slot, db) -> bool:
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
) -> list:
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
            if getattr(slot, "kind", None) == "code_digit" and slot.pos < width and slot.value is not None:
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
            candidates = [w for w in candidates if slot_constraint_matches(w, slot, db)]
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
    target_final_options: list[Optional[set[str]]] = [None] * width
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if 0 <= pos < width:
            options = anchor_phoneme_options(ch, "final", db, allow_inject=True)
            if options:
                target_final_options[pos] = options
    return target_final_options


def word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    if not final_options:
        return True
    word_finals = get_rhyme_finals(word)
    return len(word_finals) >= 2 and word_finals[-1] in final_options


def matches_final_options(word_finals: list, target_final_options: list[Optional[set[str]]]) -> bool:
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