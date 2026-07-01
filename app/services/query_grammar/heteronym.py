"""同音異讀 code/code 語法（CONTEXT § 同音異讀查詢）。"""

from __future__ import annotations

import re
from typing import Optional

from app.services.query_tokens import CANTO_CHARS_RE

HETERONYM_CODE_RE = re.compile(r"^([\d?]+)/([\d?]+)$")
HETERONYM_UNEQUAL_LENGTH_HINT = "同音異讀查詢左右碼位模板須等長。"


def parse_heteronym_code_query(q: str) -> Optional[dict]:
    if not q or "$" in q or re.search(CANTO_CHARS_RE, q):
        return None
    m = HETERONYM_CODE_RE.match(q)
    if not m:
        return None
    left, right = m.group(1), m.group(2)
    if len(left) != len(right):
        return {"kind": "heteronym_unequal", "hint": HETERONYM_UNEQUAL_LENGTH_HINT}
    return {
        "kind": "heteronym_code",
        "left_template": left,
        "right_template": right,
        "width": len(left),
    }


def code_template_to_required(left_or_right: str) -> list[Optional[str]]:
    return [None if ch == "?" else ch for ch in left_or_right]
