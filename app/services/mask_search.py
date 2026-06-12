from __future__ import annotations

import json
import re
from typing import List, Optional

from utils import get_code_variants, get_words_for_length, load_json_list

from app.models.word import Word
from app.services.phoneme_lookup import final_options_for_char, initial_options_for_char
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_query_parser import (
    build_mask_from_slots,
    mask_char_glob_pattern,
    matches_mask_literal_chars,
    parse_mask_query,
)
from app.services.word_serializer import (
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
    serialize_page,
)

def matches_phoneme_at_position(
    word,
    pos: int,
    anchor: str,
    *,
    constraint: str,
    db,
) -> bool:
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


def get_length_candidates(db, width: int, mask: str):
    candidates = get_words_for_length(width)
    if candidates:
        return [w for w in candidates if matches_mask_literal_chars(get_word_text(w), mask)], True
    glob_pat = mask_char_glob_pattern(mask)
    query = db.query(Word).filter(
        length_filter(width),
        Word.char.op("GLOB")(glob_pat),
    )
    return query.order_by(Word.char, Word.jyutping).all(), False


def handle_rhyme_anchor_query(parsed: dict, mode: str, limit: int, offset: int, db):
    width = parsed["width"]
    mask = build_mask_from_slots(parsed["slots"], width, parsed["anchor_pos"])
    candidates, _ = get_length_candidates(db, width, mask)
    filtered = filter_words_by_code_and_mask(
        candidates,
        width=width,
        code_digits="",
        mode=mode,
        mask=mask,
        db=db,
        anchor_pos=parsed["anchor_pos"],
        anchor=parsed["anchor"],
        constraint=parsed["constraint"],
    )
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def handle_code_tail_query(parsed: dict, mode: str, limit: int, offset: int, db):
    width = parsed["width"]
    code_digits = parsed["code_digits"]
    anchor_pos = parsed["anchor_pos"]
    constraint = parsed["constraint"]
    anchor = parsed["anchor"]

    if constraint == "literal":
        mask = build_mask_from_slots("", width, anchor_pos)
        mask = mask[:anchor_pos] + anchor
        literal_char = anchor
        phoneme = None
    else:
        mask = build_mask_from_slots("", width, anchor_pos)
        literal_char = None
        phoneme = constraint

    candidates, _ = get_length_candidates(db, width, mask)
    filtered = filter_words_by_code_and_mask(
        candidates,
        width=width,
        code_digits=code_digits,
        mode=mode,
        mask=mask,
        db=db,
        anchor_pos=anchor_pos if phoneme else None,
        anchor=anchor if phoneme else None,
        constraint=phoneme,
        literal_char=literal_char,
    )
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def handle_at_tail_query(parsed: dict, mode: str, limit: int, offset: int, db):
    width = parsed["width"]
    code_digits = parsed["code_digits"]
    literal = parsed["literal_char"]
    mask = "?" * (width - 1) + literal
    candidates, _ = get_length_candidates(db, width, mask)
    filtered = filter_words_by_code_and_mask(
        candidates,
        width=width,
        code_digits=code_digits,
        mode=mode,
        mask=mask,
        db=db,
        literal_char=literal,
    )
    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def get_candidates_for_length(
    db: Session,
    length: int,
    *,
    code: Optional[str] = None,
    mode: str = "m1",
    fallback_limit: int = 2000,
):
    candidates = get_words_for_length(length)
    if candidates:
        return candidates, True
    query = db.query(Word).filter(length_filter(length))
    if code:
        query = apply_code_filter(query, code, mode)
    return query.order_by(Word.char, Word.jyutping).limit(fallback_limit).all(), False


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
            options = final_options_for_char(ch, db)
            if options:
                target_final_options[pos] = options
    return target_final_options


def word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    if not final_options:
        return True
    word_finals = get_word_parts(word, "finals")
    return len(word_finals) >= 2 and word_finals[-1] in final_options


def matches_code_positions(code_str: str, required_codes: list[Optional[str]], mode: str) -> bool:
    if len(code_str) != len(required_codes):
        return False
    for idx, req_digit in enumerate(required_codes):
        if req_digit is None:
            continue
        if code_str[idx] not in set(get_code_variants(req_digit, mode)):
            return False
    return True


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
    char = get_word_text(word)
    jyutping = get_word_jyutping(word)
    exact_count = sum(1 for pos, ch in literal_positions if pos < len(char) and char[pos] == ch)
    return (-exact_count, char, jyutping)


def handle_hybrid_syntax(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):  # untyped db to avoid FastAPI treating it as a response field during module import
    """處理 hybrid（數字前綴 + 粵字 + 數字後綴）語法。"""
    hybrid_match = re.match(r'^(\d+)([一-龥]+)(\d*)$', q)
    if not hybrid_match:
        return []

    num_prefix = hybrid_match.group(1)
    ref_chars = hybrid_match.group(2)
    num_suffix = hybrid_match.group(3)

    full_code = num_prefix + num_suffix
    ref_pos = max(0, len(num_prefix) - 1)

    candidates, used_cache = get_candidates_for_length(
        db, len(full_code), code=full_code, mode=mode,
    )
    target_final_options = build_final_options_at_positions(
        ref_chars, ref_pos, len(full_code), db,
    )

    filtered = []
    allowed_full_codes = set(get_code_variants(full_code, mode))
    for word in candidates:
        if used_cache:
            if not word.get("finals") or not word.get("code"):
                continue
            word_finals = word.get("finals") or []
            word_code_str = word.get("code") or ""
        else:
            if not word.finals or not word.code:
                continue
            try:
                word_finals = json.loads(word.finals)
            except (TypeError, json.JSONDecodeError):
                continue
            word_code_str = word.code or ""
        if word_code_str not in allowed_full_codes:
            continue
        word_char = word.get("char") if used_cache else (word.char or "")
        if matches_hybrid_ref_chars(
            word_char, word_finals, ref_chars, ref_pos, target_final_options,
        ):
            filtered.append(word)

    filtered.sort(key=lambda w: (get_word_text(w), get_word_jyutping(w)))
    return serialize_page(filtered, offset, limit)


def handle_mask_wildcard_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):
    """Handle mask queries: literal canto chars match by position first, then code digits."""
    mask = q
    expected_len, required_codes, literal_positions = parse_mask_query(mask)
    if expected_len == 0:
        return []

    glob_pat = mask_char_glob_pattern(mask)
    candidates = get_words_for_length(expected_len)
    used_cache = bool(candidates)
    if used_cache:
        candidates = [
            w for w in candidates
            if matches_mask_literal_chars(get_word_text(w), mask)
        ]
    else:
        query = db.query(Word).filter(
            length_filter(expected_len),
            Word.char.op("GLOB")(glob_pat),
        )
        code_filter = "".join(required_codes) if all(req is not None for req in required_codes) else None
        if code_filter:
            query = apply_code_filter(query, code_filter, mode)
        candidates = query.order_by(Word.char, Word.jyutping).all()

    filtered = []
    for word in candidates:
        word_char = get_word_text(word)
        if not matches_mask_literal_chars(word_char, mask):
            continue
        word_code_str = get_word_sort_code(word)
        word_finals = get_word_parts(word, "finals")
        if not word_code_str or not word_finals:
            continue
        if not matches_code_positions(word_code_str, required_codes, mode):
            continue
        filtered.append(word)

    filtered.sort(key=lambda item: mask_priority_key(item, literal_positions))
    return serialize_page(filtered, offset, limit)
