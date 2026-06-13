"""近反義候選字面規則 — ingest 與 runtime 近反義池共用。"""

from __future__ import annotations

import re

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
MAX_WORD_LEN = 12


def clean_term(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"[（(].*?[）)]", "", t)
    t = re.sub(r"\s+", "", t)
    return t


def is_valid_term(text: str) -> bool:
    if not text or len(text) > MAX_WORD_LEN:
        return False
    if not CJK_RE.search(text):
        return False
    if re.search(r"[0-9A-Za-z_]", text):
        return False
    return True


def normalize_literal(text: str) -> str | None:
    """clean_term + is_valid_term；無效則 None。"""
    t = clean_term(text)
    if not is_valid_term(t):
        return None
    return t


__all__ = [
    "CJK_RE",
    "MAX_WORD_LEN",
    "clean_term",
    "is_valid_term",
    "normalize_literal",
]
