"""Unicode Han-script predicates shared by ingest and runtime trust boundaries."""
from __future__ import annotations

import re

# Unicode 17 Script=Han ranges needed by Python's stdlib ``re``.  Keep this
# centralized; JavaScript peers use ``\p{Script=Han}`` with the ``u`` flag.
HAN_CLASS = (
    "\u2e80-\u2eff\u2f00-\u2fdf\u3005\u3007\u3021-\u3029"
    "\u3038-\u303b\u31c0-\u31ef\u3400-\u4dbf\u4e00-\u9fff"
    "\uf900-\ufaff\U00020000-\U0002ee5f\U00030000-\U0003347f"
)
HAN_RE = re.compile(f"[{HAN_CLASS}]")
HAN_ONLY_RE = re.compile(f"^[{HAN_CLASS}]+$")


def is_han_char(char: str) -> bool:
    return len(char) == 1 and bool(HAN_ONLY_RE.fullmatch(char))


def contains_han(text: str) -> bool:
    return bool(text and HAN_RE.search(text))


def is_han_text(text: str) -> bool:
    return bool(text and HAN_ONLY_RE.fullmatch(text))


__all__ = ["HAN_CLASS", "HAN_RE", "HAN_ONLY_RE", "contains_han", "is_han_char", "is_han_text"]
