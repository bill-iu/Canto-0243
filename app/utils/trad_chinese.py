"""Simplified → Traditional for relation literals (project canonical form)."""

from __future__ import annotations

from functools import lru_cache

# OpenCC s2t collapses 霉→黴. Keep fortune/luck compounds on 霉;
# mold/fungus senses (發黴、黴菌、×黴素) stay on 黴.
_MOU_FORTUNE_RESTORE: tuple[tuple[str, str], ...] = (
    ("黴運", "霉運"),
    ("倒黴", "倒霉"),
    ("觸黴頭", "觸霉頭"),
    ("黴氣", "霉氣"),
    ("黴天", "霉天"),
    ("黴雨", "霉雨"),
    ("黴爛", "霉爛"),
)


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
    out = converter.convert(text)
    for bad, good in _MOU_FORTUNE_RESTORE:
        out = out.replace(bad, good)
    return out


__all__ = ["to_traditional"]


if __name__ == "__main__":
    # ponytail: smoke — OpenCC must not collapse fortune-霉 into mold-黴
    assert to_traditional("霉運") == "霉運"
    assert to_traditional("倒霉") == "倒霉"
    assert to_traditional("发霉") == "發黴"
    assert to_traditional("黴菌") == "黴菌"
    print("trad_chinese mou/mei ok")
