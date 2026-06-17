"""星號錨 grammar — normalize 收尾、mask 快路、parse（#3 下一輪）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services.query_grammar import rhyme as rhyme_grammar
from app.services.query_grammar import serial as serial_grammar
from app.services.query_grammar.equals import is_framed_equals_query
from app.services.query_tokens import CODE_TAIL_MIDDLE

CODE_TAIL_RE = re.compile(rf"^(\d+){re.escape(CODE_TAIL_MIDDLE)}(.+)$")
AT_TAIL_RE = re.compile(r"^(\d+)@([一-龥])$")

_HEAD_LITERAL_TAIL_RE = re.compile(r"[_?%0-9=]")
_MIDDLE_WILDCARD_BEFORE_CANTO_RE = re.compile(
    rf"(?<![0-9*])([{re.escape('?_')}%])([一-龥])(?!=)"
)


def normalize_canonical_star_query(q: str) -> str:
    """P0：首格字面 *X…、通配左中格 ?*字…（碼左參考字、韻錨、等號查詢唔插 *）。"""
    if not q or "*" in q:
        return q
    if serial_grammar.blocks_star_normalize(q):
        return q
    if is_framed_equals_query(q):
        return q
    if rhyme_grammar.blocks_star_normalize(q):
        return q
    m = re.match(r"^([一-龥])(.+)$", q)
    if m:
        tail = m.group(2)
        if tail.startswith("="):
            return q
        if _HEAD_LITERAL_TAIL_RE.search(tail):
            return "*" + q
    return _MIDDLE_WILDCARD_BEFORE_CANTO_RE.sub(r"\1*\2", q)


def mask_from_canonical_star_query(q: str) -> Optional[str]:
    """`*` 規範缺字串 → 等價 mask（與 normalize 後首格／中格字面 MaskQuery 同一 MatchSpec）。"""
    if not q or "=" in q:
        return None
    m = re.match(r"^\*([一-龥][0-9_?%]+)$", q)
    if m:
        return m.group(1)
    m = re.match(r"^([_?%])\*([一-龥])([0-9_?%]*)$", q)
    if m:
        return m.group(1) + m.group(2) + m.group(3)
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


def parse_star_anchor_query(q: str) -> Optional[dict]:
    """
    Star-anchor family (綜合頭/中/尾格):

    - 尾格（既有）: {code}*{漢字}{可選 '='}  /  {code}*= {漢字}（同聲母，legacy）
    - 中格（新增）: {left_code}*{漢字}{可選 '='}{right_code}
    - 頭格（新增）: *{漢字}{可選 '='}{right_code}
    """
    if not q or CODE_TAIL_MIDDLE not in q or "@" in q:
        return None

    m = re.match(r"^\*([一-龥])(=)?(\d+)$", q)
    if m:
        anchor, eq, right = m.group(1), m.group(2), m.group(3)
        width = 1 + len(right)
        anchor_pos = 0
        return {
            "width": width,
            "anchor_pos": anchor_pos,
            "anchor": anchor,
            "constraint": "final" if eq else "literal",
            "code_slots": [(anchor_pos + 1 + i, d) for i, d in enumerate(right)],
            "code_prefix": None,
        }

    m = re.match(r"^(\d+)\*([一-龥])(=)?(\d+)$", q)
    if m:
        left, anchor, eq, right = m.group(1), m.group(2), m.group(3), m.group(4)
        anchor_pos = len(left)
        width = len(left) + 1 + len(right)
        code_slots = [(i, d) for i, d in enumerate(left)] + [
            (anchor_pos + 1 + i, d) for i, d in enumerate(right)
        ]
        return {
            "width": width,
            "anchor_pos": anchor_pos,
            "anchor": anchor,
            "constraint": "final" if eq else "literal",
            "code_slots": code_slots,
            "code_prefix": None,
        }

    m = re.match(r"^(\d+)\*([一-龥])(=)?$", q)
    if m:
        code, anchor, eq = m.group(1), m.group(2), m.group(3)
        width = len(code) + 1
        return {
            "width": width,
            "anchor_pos": width - 1,
            "anchor": anchor,
            "constraint": "final" if eq else "literal",
            "code_slots": [(i, d) for i, d in enumerate(code)],
            "code_prefix": code,
        }

    m = re.match(r"^(\d+)\*=([一-龥])$", q)
    if m:
        code, anchor = m.group(1), m.group(2)
        width = len(code) + 1
        return {
            "width": width,
            "anchor_pos": width - 1,
            "anchor": anchor,
            "constraint": "initial",
            "code_slots": [(i, d) for i, d in enumerate(code)],
            "code_prefix": code,
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
