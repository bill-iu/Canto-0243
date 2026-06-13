from __future__ import annotations

import re
from typing import Optional

WILDCARD_CHARS = frozenset("_?%")
CODE_TAIL_MIDDLE = "*"
LEGACY_CODE_TAIL_SEPARATORS = ("&", "\u00b7")

CODE_TAIL_RE = re.compile(rf"^(\d+){re.escape(CODE_TAIL_MIDDLE)}(.+)$")
HYBRID_TAIL_EQUALS_RE = re.compile(r"^(\d+)([一-龥])=$")
AT_TAIL_RE = re.compile(r"^(\d+)@([一-龥])$")
SLOT_CHARS_RE = r"[0-9_?%]"

RELATION_LOOKUP_RE = re.compile(r"^(\d*)([~!])([\u4e00-\u9fff]+)$")
COMPOUND_SYN_RE = re.compile(r"^(\d*)~~([\u4e00-\u9fff])?$")
COMPOUND_ANT_RE = re.compile(r"^(\d*)!!([\u4e00-\u9fff])?$")


def normalize_code_tail_separators(q: str) -> str:
    """Map legacy code-tail separators (&, ·) to * only at digit-prefix positions."""
    m = re.match(r"^(\d+)([&·*])(.+)$", q)
    if not m:
        return q
    sep = m.group(2)
    if sep in LEGACY_CODE_TAIL_SEPARATORS:
        return f"{m.group(1)}{CODE_TAIL_MIDDLE}{m.group(3)}"
    return q


def is_hybrid_tail_equals_alias(q: str) -> bool:
    """True for 23就= style queries that alias hybrid tail-rhyme (23就)."""
    return bool(HYBRID_TAIL_EQUALS_RE.match(q))


def hybrid_query_from_tail_equals(q: str) -> str:
    return q[:-1]


def is_wildcard_char(ch: str) -> bool:
    return len(ch) == 1 and ch in WILDCARD_CHARS


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


def mask_char_glob_pattern(mask: str) -> str:
    """Build SQLite GLOB for Word.char: wildcard/digit slots -> ?, literals unchanged."""
    return "".join(
        "?" if (is_wildcard_char(ch) or ch.isdigit()) else ch
        for ch in mask
    )


def matches_mask_literal_chars(word_char: str, mask: str) -> bool:
    """True when every non-wildcard, non-digit mask slot equals the word character."""
    if len(word_char) != len(mask):
        return False
    for idx, ch in enumerate(mask):
        if is_wildcard_char(ch) or ch.isdigit():
            continue
        if word_char[idx] != ch:
            return False
    return True


def looks_like_mask_query(q: str) -> bool:
    """True when q uses position mask syntax (digits / canto / wildcards)."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q:
        return False
    if parse_rhyme_anchor_query(q):
        return False
    if not re.match(r"^[0-9_?%一-龥]+$", q):
        return False
    has_wild = any(is_wildcard_char(c) for c in q)
    has_digit = any(c.isdigit() for c in q)
    has_canto = any(not c.isdigit() and not is_wildcard_char(c) for c in q)
    return has_wild or (has_digit and has_canto)


def is_framed_equals_query(q: str) -> bool:
    """Legacy framed equals: 香港=, 2=我3 — not query-level rhyme anchors or hybrid tail alias."""
    if CODE_TAIL_MIDDLE in q or "@" in q or is_hybrid_tail_equals_alias(q):
        return False
    match = re.match(r"^(\d*)(=)?([一-龥]+)(=)?(\d*)$", q)
    if not match:
        return False
    target = match.group(3) or ""
    if not target:
        return False
    left_code = match.group(1) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_equal = bool(match.group(2))
    if right_equal and len(target) >= 2:
        return True
    if right_equal and left_code and len(target) == 1:
        return True
    if inner_equal and left_code and right_code:
        return True
    if inner_equal and left_code and not right_equal:
        return True  # 34=我：左碼 + 內嵌 = + 參考字，無右碼
    if inner_equal and not left_code and not right_code and len(target) >= 2:
        return True  # =香港：整詞同聲（與 香港= 整詞同韻對稱）
    return False


def parse_rhyme_anchor_query(q: str) -> Optional[dict]:
    """Query-level rhyme anchor: 香=? / ?就= / =香? / ?=就 (no code-tail *)."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q or is_framed_equals_query(q):
        return None

    m = re.match(rf"^({SLOT_CHARS_RE}+)([一-龥])=$", q)
    if m:
        slots, anchor = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "final",
            "anchor_pos": width - 1,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^([一-龥])=({SLOT_CHARS_RE}+)$", q)
    if m:
        anchor, slots = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "final",
            "anchor_pos": 0,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^=([一-龥])({SLOT_CHARS_RE}+)$", q)
    if m:
        anchor, slots = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "initial",
            "anchor_pos": 0,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^({SLOT_CHARS_RE}+)=([一-龥])$", q)
    if m:
        slots, anchor = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "initial",
            "anchor_pos": width - 1,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }
    return None


def parse_code_tail_query(q: str) -> Optional[dict]:
    if CODE_TAIL_MIDDLE not in q:
        return None
    m = CODE_TAIL_RE.match(q)
    if not m:
        return None
    code_digits = m.group(1)
    tail = m.group(2)
    width = len(code_digits) + 1

    m2 = re.match(r"^([一-龥])=$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "final",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }

    m2 = re.match(r"^=([一-龥])$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "initial",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }

    m2 = re.match(r"^([一-龥])$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "literal",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }
    return None


def parse_at_tail_query(q: str) -> Optional[dict]:
    m = AT_TAIL_RE.match(q)
    if not m:
        return None
    return {
        "code_digits": m.group(1),
        "literal_char": m.group(2),
        "width": len(m.group(1)),
    }


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


def parse_relation_syntax(q: str) -> Optional[dict]:
    """Parse 0243 relation syntax: ~~ compound syn, !! compound ant, ~syn, !ant."""
    compound_syn = COMPOUND_SYN_RE.match(q)
    if compound_syn:
        prefix = compound_syn.group(1) or ""
        rhyme_char = compound_syn.group(2) or None
        return {
            "kind": "compound_syn",
            "code_prefix": prefix or None,
            "rhyme_char": rhyme_char,
        }

    compound = COMPOUND_ANT_RE.match(q)
    if compound:
        prefix = compound.group(1) or ""
        rhyme_char = compound.group(2) or None
        return {
            "kind": "compound_ant",
            "code_prefix": prefix or None,
            "rhyme_char": rhyme_char,
        }

    lookup = RELATION_LOOKUP_RE.match(q)
    if lookup:
        prefix = lookup.group(1) or ""
        op = lookup.group(2)
        word = lookup.group(3)
        return {
            "kind": "syn" if op == "~" else "ant",
            "code_prefix": prefix or None,
            "word": word,
        }
    return None