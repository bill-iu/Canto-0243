"""Simplified → Traditional for relation literals (project canonical form)."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _s2t_converter():
    try:
        import opencc

        return opencc.OpenCC("s2t")
    except ImportError:
        return None


def to_traditional(text: str) -> str:
    if not text:
        return text
    converter = _s2t_converter()
    if converter is None:
        return text
    return converter.convert(text)


__all__ = ["to_traditional"]