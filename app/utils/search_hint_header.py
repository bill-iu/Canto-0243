"""RFC 5987 encoding for non-ASCII X-Search-Hint values (HTTP headers are latin-1)."""
from __future__ import annotations

from urllib.parse import quote, unquote

_UTF8_PARAM_PREFIX = "UTF-8''"


def encode_search_hint(value: str) -> str:
    if value.isascii():
        return value
    return f"{_UTF8_PARAM_PREFIX}{quote(value, safe='')}"


def decode_search_hint(value: str) -> str:
    if value.startswith(_UTF8_PARAM_PREFIX):
        return unquote(value[len(_UTF8_PARAM_PREFIX) :], encoding="utf-8")
    return value
