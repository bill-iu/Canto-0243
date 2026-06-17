"""缺字 mask grammar（#3 收尾）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services.query_tokens import CODE_TAIL_MIDDLE, is_wildcard_char


def parse_mask_query(mask: str) -> tuple[int, list[Optional[str]], list[tuple[int, str]]]:
    """Split mask into length, per-position code digits, and literal canto positions."""
    expected_len = len(mask)
    required_codes: list[Optional[str]] = [None] * expected_len
    literal_positions: list[tuple[int, str]] = []
    for idx, ch in enumerate(mask):
        if is_wildcard_char(ch):
            continue
        if ch.isdigit():
            required_codes[idx] = ch
            continue
        literal_positions.append((idx, ch))
    return expected_len, required_codes, literal_positions


def looks_like_mask_query(q: str) -> bool:
    """True when q uses position mask syntax (digits / canto / wildcards)."""
    from app.services.query_parse import try_parse_before_mask

    if not q or CODE_TAIL_MIDDLE in q or "@" in q:
        return False
    if try_parse_before_mask(q) is not None:
        return False
    if not re.match(r"^[0-9_?%一-龥]+$", q):
        return False
    has_wild = any(is_wildcard_char(c) for c in q)
    has_digit = any(c.isdigit() for c in q)
    has_canto = any(not c.isdigit() and not is_wildcard_char(c) for c in q)
    return has_wild or (has_digit and has_canto)


def build_mask_from_slots(slots: str, width: int, anchor_pos: int) -> str:
    """Build a literal-mask string with anchor position as wildcard."""
    chars = ["?"] * width
    if anchor_pos == 0:
        for i, ch in enumerate(slots, start=1):
            chars[i] = ch
    else:
        for i, ch in enumerate(slots):
            chars[i] = ch
    return "".join(chars)
