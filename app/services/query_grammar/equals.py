"""等號查詢 grammar stub（#3 下一輪；完整 equals 家族待搬）。"""
from __future__ import annotations

import re

from app.services.query_tokens import CODE_TAIL_MIDDLE

HYBRID_TAIL_EQUALS_RE = re.compile(r"^(\d+)([一-龥])=$")


def is_hybrid_tail_equals_alias(q: str) -> bool:
    """True for 23就= style queries that alias hybrid tail-rhyme (23就)."""
    return bool(HYBRID_TAIL_EQUALS_RE.match(q))


def hybrid_query_from_tail_equals(q: str) -> str:
    return q[:-1]


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
        return True
    if inner_equal and not left_code and not right_code and len(target) >= 2:
        return True
    return False
