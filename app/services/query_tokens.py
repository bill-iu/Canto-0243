"""查詢語法共用常數與 regex（lexer／grammar 共用）。"""
from __future__ import annotations

import re

WILDCARD_CHARS = frozenset("_?%")
CODE_TAIL_MIDDLE = "+"
LEGACY_CODE_TAIL_SEPARATORS = ("&", "\u00b7", "*")

CANTO_CHARS_RE = re.compile(r"[\u4e00-\u9fff]")

CONSECUTIVE_SLOT_CONNECTOR_HINT = (
    "唔支援連續 `+`：通配音節請用 `?`，slot 連接符最多一個。"
    "例：`?30?+人`（唔好寫 `?30++人`）。"
    "（輸入 `*` 仍接受，等同 `+`。）"
)
DIGIT_AFTER_SLOT_CONNECTOR_HINT = (
    "`+` 後須接漢字或粵拼錨，唔可以接碼。"
    "例：尾格用 `2+好3` 或 `2+好人`。"
    "（輸入 `*` 仍接受，等同 `+`。）"
)

SERIAL_CHARSET_RE = re.compile(r"^[0-9?=一-龥]+$")
SLOT_CHARS_RE = r"[0-9_?%]"


def is_wildcard_char(ch: str) -> bool:
    return len(ch) == 1 and ch in WILDCARD_CHARS
