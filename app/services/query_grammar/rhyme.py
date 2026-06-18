"""韻／聲錨 grammar（#3 第三輪）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services.query_grammar.equals import (
    is_framed_equals_query,
    is_hybrid_tail_equals_alias,
)
from app.services.query_tokens import CODE_TAIL_MIDDLE, SLOT_CHARS_RE, WILDCARD_CHARS

_RHYME_ANCHOR_SHAPE_RE = re.compile(
    rf"^(?:"
    rf"({SLOT_CHARS_RE}+)([一-龥])=$|"
    rf"([一-龥])=({SLOT_CHARS_RE}+)$|"
    rf"=([一-龥])({SLOT_CHARS_RE}+)$|"
    rf"({SLOT_CHARS_RE}+)=([一-龥])$"
    rf")"
)


def _is_wildcard_char(ch: str) -> bool:
    return len(ch) == 1 and ch in WILDCARD_CHARS


def normalize_partial_rhyme_mask_query(q: str) -> str:
    """`窮困潦=?` → `窮困潦?=`（尾格通配 + 韻錨）。"""
    m = re.fullmatch(r"^([一-龥]{3})=\?$", q)
    if m:
        return f"{m.group(1)}?="
    return q


def parse_partial_rhyme_mask_query(q: str) -> Optional[dict]:
    """四字部分韻錨：`窮?潦倒=` 等；`?` 通配，其餘格同參考字韻母。"""
    nq = normalize_partial_rhyme_mask_query(q)
    m = re.fullmatch(r"^([一-龥?]{4})=$", nq)
    if not m:
        return None
    pattern = m.group(1)
    if "?" not in pattern or all(ch == "?" for ch in pattern):
        return None
    if pattern.startswith("?") and re.fullmatch(r"\?[一-龥]{3}", pattern):
        return None
    anchors = [(pos, ch) for pos, ch in enumerate(pattern) if ch != "?"]
    if not anchors:
        return None
    return {"raw_q": q, "pattern": pattern, "width": 4, "anchors": anchors}


def blocks_star_normalize(q: str) -> bool:
    """韻／聲錨形狀 — star normalize 唔插 `*`。"""
    if parse_partial_rhyme_mask_query(q):
        return True
    return bool(_RHYME_ANCHOR_SHAPE_RE.match(q))


def parse_code_ref_rhyme_contradiction_hint(q: str) -> Optional[str]:
    """?3人? 無 = → hint（P3）。"""
    m = re.match(r"^([?_%]+)(\d+)([一-龥])([?_%])$", q)
    if m and "=" not in q:
        d, ref = m.group(2), m.group(3)
        return f"碼位同參考字「{ref}」衝突：請改用 `?{d}{ref}=?` 標中格同韻。"
    return None


def parse_code_ref_middle_rhyme_query(q: str) -> Optional[dict]:
    """碼＋參考字＋通配（中格韻）：?3人=?（P3）。"""
    m = re.match(r"^([?_%]+)(\d+)([一-龥])=\?$", q)
    if not m:
        return None
    leading, digits, anchor = m.group(1), m.group(2), m.group(3)
    width = len(leading) + len(digits) + 1
    anchor_pos = len(leading) + len(digits) - 1
    slots: list[dict] = []
    for i, d in enumerate(digits):
        slots.append({"pos": len(leading) + i, "kind": "code_digit", "value": d})
    slots.append({"pos": anchor_pos, "kind": "final_anchor", "value": anchor})
    return {
        "raw_q": q,
        "width": width,
        "anchor": anchor,
        "anchor_pos": anchor_pos,
        "leading": leading,
        "digits": digits,
        "slots": slots,
    }


def parse_double_wildcard_rhyme_query(q: str) -> Optional[dict]:
    """二字韻錨 ?*就=（P2）。"""
    m = re.match(r"^([?_%])\*([一-龥])=$", q)
    if not m:
        return None
    return {
        "constraint": "final",
        "anchor": m.group(2),
        "anchor_pos": 1,
        "slots": m.group(1),
        "width": 2,
    }


def parse_double_wildcard_initial_query(q: str) -> Optional[dict]:
    """二字聲錨 ?*=就（P2 對稱）。"""
    m = re.match(r"^([?_%])\*=([一-龥])$", q)
    if not m:
        return None
    return {
        "constraint": "initial",
        "anchor": m.group(2),
        "anchor_pos": 1,
        "slots": m.group(1),
        "width": 2,
    }


def parse_rhyme_anchor_query(q: str) -> Optional[dict]:
    """Query-level rhyme/initial anchor: 就= / =就 / 香=? / ?*就= / =香? / ?*=就."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q or is_framed_equals_query(q):
        return None
    if parse_double_wildcard_rhyme_query(q) or parse_double_wildcard_initial_query(q):
        return None

    m = re.match(r"^([一-龥])=$", q)
    if m:
        return {
            "constraint": "final",
            "anchor": m.group(1),
            "anchor_pos": 0,
            "slots": "",
            "width": 1,
        }

    m = re.match(r"^=([一-龥])$", q)
    if m:
        return {
            "constraint": "initial",
            "anchor": m.group(1),
            "anchor_pos": 0,
            "slots": "",
            "width": 1,
        }

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


def parse_triple_rhyme_anchor_query(q: str) -> Optional[dict]:
    """中格同韻三字：規範形 ?*{參考字}=?（?{字}=? normalize 後）。"""
    if not q or "@" in q or is_framed_equals_query(q):
        return None
    if is_hybrid_tail_equals_alias(q):
        return None

    m = re.match(r"^(\?\*)([一-龥])=\?$", q)
    if m:
        anchor = m.group(2)
        return {
            "anchor": anchor,
            "anchor_pos": 1,
            "width": 3,
            "leading_slots": m.group(1),
            "constraint": "final",
        }

    if CODE_TAIL_MIDDLE in q:
        return None

    m = re.match(rf"^({SLOT_CHARS_RE}+)([一-龥])=(\?)$", q)
    if not m:
        return None
    leading, anchor, _trail = m.group(1), m.group(2), m.group(3)
    if not any(_is_wildcard_char(c) for c in leading):
        return None
    if re.search(r"\d", leading):
        return None
    anchor_pos = len(leading)
    width = anchor_pos + 2
    return {
        "anchor": anchor,
        "anchor_pos": anchor_pos,
        "width": width,
        "leading_slots": leading,
        "constraint": "final",
    }
