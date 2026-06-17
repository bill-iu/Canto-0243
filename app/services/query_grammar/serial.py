"""串列韻／聲錨、前綴通配等號 grammar（#3 試點）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services.query_grammar.equals import is_framed_equals_query
from app.services.query_tokens import CODE_TAIL_MIDDLE, SERIAL_CHARSET_RE

PURE_CHARS_SERIAL_HINT = (
    "每個 `{字}=`／`={字}` 前須有 0243 碼。"
    "例：`04困=49倒=`（唔好寫 `窮困=潦倒=`）。"
)
PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT = (
    "前綴通配等號查詢須以 `=` 結尾。"
    "例：`?困潦倒=`（唔好漏尾格 `=`）。"
)


def blocks_star_normalize(q: str) -> bool:
    """串列／前綴通配等號形狀 — star normalize 唔插 `*`。"""
    if re.match(r"^\?([一-龥]{2,})=$", q):
        return True
    if re.match(r"^\?[一-龥]{2,}$", q):
        return True
    if (
        re.fullmatch(r"[一-龥=]+", q)
        and re.search(r"(?<![0-9])([一-龥])=", q)
        and not re.fullmatch(r"[一-龥]=", q)
    ):
        return True
    if SERIAL_CHARSET_RE.match(q) and re.search(r"\d[一-龥]=", q):
        return True
    return False


def prefix_wildcard_equals_missing_eq_hint(q: str) -> Optional[str]:
    if re.fullmatch(r"\?[一-龥]{2,}", q):
        return PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT
    return None


def parse_pure_chars_serial_hint(q: str) -> Optional[str]:
    if not q or not re.fullmatch(r"[一-龥=]+", q):
        return None
    if re.fullmatch(r"[一-龥]=", q):
        return None
    if is_framed_equals_query(q):
        return None
    if re.search(r"(?<![0-9])([一-龥])=", q):
        return PURE_CHARS_SERIAL_HINT
    return None


def parse_prefix_wildcard_equals_query(q: str) -> Optional[dict]:
    m = re.fullmatch(r"\?([一-龥]{2,})=$", q)
    if not m:
        return None
    inner = f"{m.group(1)}="
    return {"raw_q": q, "inner_q": inner, "ref_literal": m.group(1), "width": len(m.group(1)) + 1}


def _scan_serial_phoneme(q: str, constraint: str) -> Optional[dict]:
    i = 0
    pos = 0
    code_slots: list[tuple[int, str]] = []
    anchors: list[tuple[int, str]] = []
    mask_chars: list[str] = []
    while i < len(q):
        ch = q[i]
        if ch == "?":
            mask_chars.append("?")
            pos += 1
            i += 1
            continue
        if ch.isdigit():
            if constraint == "final":
                m = re.match(r"^(\d)([一-龥])=(?=[0-9?=]|$)", q[i:])
            else:
                m = re.match(r"^(\d)=([一-龥])(?=[0-9?=]|$)", q[i:])
            if m:
                digit, anchor = m.group(1), m.group(2)
                code_slots.append((pos, digit))
                anchors.append((pos, anchor))
                mask_chars.append(digit)
                pos += 1
                i += len(m.group(0))
                continue
            code_slots.append((pos, ch))
            mask_chars.append(ch)
            pos += 1
            i += 1
            continue
        return None
    if not anchors:
        return None
    return {
        "width": pos,
        "constraint": constraint,
        "code_slots": code_slots,
        "anchors": anchors,
        "mask": "".join(mask_chars),
    }


def framed_equals_blocks_serial(q: str) -> bool:
    """碼夾／整詞等號唔走串列（G2）。"""
    if not is_framed_equals_query(q):
        return False
    m = re.match(r"^(\d*)(=)?([一-龥]+)(=)?(\d*)$", q)
    if not m:
        return False
    if m.group(2):
        return True
    if m.group(5):
        return True
    if m.group(4) and len(m.group(3)) >= 2:
        return True
    return False


def parse_serial_phoneme_anchor_query(q: str) -> Optional[dict]:
    if not q or not SERIAL_CHARSET_RE.match(q):
        return None
    if CODE_TAIL_MIDDLE in q or "@" in q or "*" in q or "_" in q or "%" in q:
        return None
    if framed_equals_blocks_serial(q):
        return None
    if re.fullmatch(r"[一-龥]=", q):
        return None
    has_rhyme = bool(re.search(r"\d[一-龥]=", q))
    has_initial = bool(re.search(r"\d=[一-龥]", q))
    if has_rhyme and has_initial:
        return None
    constraint = "final" if has_rhyme else "initial"
    if not has_rhyme and not has_initial:
        return None
    parsed = _scan_serial_phoneme(q, constraint)
    if not parsed:
        return None
    parsed["raw_q"] = q
    return parsed
