"""查詢 lexer — normalize 全鏈（#3 試點；canonical star 仍由 facade 收尾）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services.query_tokens import (
    CANTO_CHARS_RE,
    CODE_TAIL_MIDDLE,
    CONSECUTIVE_SLOT_CONNECTOR_HINT,
    DIGIT_AFTER_SLOT_CONNECTOR_HINT,
    LEGACY_CODE_TAIL_SEPARATORS,
)


def normalize_code_tail_separators(q: str) -> str:
    """Map legacy code-tail separators (&, ·) to * only at digit-prefix positions."""
    m = re.match(r"^(\d+)([&·*])(.+)$", q)
    if not m:
        return q
    sep = m.group(2)
    if sep in LEGACY_CODE_TAIL_SEPARATORS:
        return f"{m.group(1)}{CODE_TAIL_MIDDLE}{m.group(3)}"
    return q


def normalize_query_syntax(q: str) -> str:
    """Full-width relation/wildcard punctuation → ASCII (查詢分派入口)."""
    q = q.replace("＊", "*").replace("﹡", "*")
    q = q.replace("＋", "+")
    q = q.replace("+", "*")
    q = q.replace("！！", "!!").replace("～～", "~~")
    return q.replace("！", "!").replace("～", "~").replace("？", "?")


def normalize_jyutping_slot_connectors(q: str) -> str:
    """ADR-0013：缺字型粵拼錨 slot 連接符規範化（?hon→?*hon、3?ngo4→3*ngo4）。"""
    if not q or re.search(CANTO_CHARS_RE, q):
        m = re.match(r"^(\d)\?([a-zA-Z]+)(\d)$", q)
        if m:
            return f"{m.group(1)}*{m.group(2)}{m.group(3)}"
        return q
    m = re.match(r"^(\?)([a-zA-Z]+)(\?)$", q)
    if m and "*" not in q:
        return f"?*{m.group(2)}?"
    m = re.match(r"^(\?)([a-zA-Z]+)$", q)
    if m and "*" not in q:
        return f"?*{m.group(2)}"
    m = re.match(r"^(\d)\?([a-zA-Z]+)(\d)$", q)
    if m:
        return f"{m.group(1)}*{m.group(2)}{m.group(3)}"
    return q


def slot_connector_syntax_error(q: str) -> Optional[str]:
    """連續 ** 或 * 後接碼 → hint 文案。"""
    if "**" in q:
        return CONSECUTIVE_SLOT_CONNECTOR_HINT
    if re.search(r"\*\d", q):
        return DIGIT_AFTER_SLOT_CONNECTOR_HINT
    return None


def normalize_redundant_single_char_rhyme(q: str) -> str:
    """?{單字}= → {單字}=（冗餘前導 ?）。"""
    m = re.match(r"^(\?)([一-龥])=$", q)
    if m:
        return f"{m.group(2)}="
    return q


def normalize_redundant_single_char_initial(q: str) -> str:
    """?={單字} → ={單字}（冗餘前導 ?）。"""
    m = re.match(r"^(\?)=([一-龥])$", q)
    if m:
        return f"={m.group(2)}"
    return q


def normalize_middle_rhyme_triple(q: str) -> str:
    """?{字}=? → ?*{字}=?（中格同韻三字；中間無數字）。"""
    m = re.match(r"^\?([一-龥])=\?$", q)
    if m:
        return f"?*{m.group(1)}=?"
    return q


def normalize_search_query_core(q: str) -> str:
    """normalize 主鏈（不含 canonical star）。"""
    from app.services.query_grammar.rhyme import (
        normalize_partial_initial_mask_query,
        normalize_partial_rhyme_mask_query,
    )

    q = normalize_query_syntax(normalize_code_tail_separators(q.strip()))
    q = normalize_partial_rhyme_mask_query(q)
    q = normalize_partial_initial_mask_query(q)
    q = normalize_jyutping_slot_connectors(q)
    q = normalize_redundant_single_char_rhyme(q)
    q = normalize_redundant_single_char_initial(q)
    q = normalize_middle_rhyme_triple(q)
    return q


def normalize_search_query(q: str) -> str:
    """查詢分派入口：strip、code-tail、全形標點、星號槽規範化。"""
    from app.services.query_grammar.star import normalize_canonical_star_query

    return normalize_canonical_star_query(normalize_search_query_core(q))
