"""Simplified → Traditional for relation literals (project canonical form).

Cantonese product orthography follows HK conventions via OpenCC ``s2hk``.
Plain ``s2t`` wrongly maps 核-as-verify compounds to 覈 (覈實、審覈…).
"""

from __future__ import annotations

from functools import lru_cache

# OpenCC collapses 霉→黴. Keep fortune/luck compounds on 霉;
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
def _s2hk_converter():
    try:
        import opencc

        return opencc.OpenCC("s2hk")
    except ImportError:
        return None


def to_traditional(text: str) -> str:
    if not text:
        return text
    converter = _s2hk_converter()
    out = converter.convert(text) if converter is not None else text
    # ponytail: without OpenCC, still collapse 覈→核 (HKVariants); ceiling = rare literary 覈
    out = out.replace("覈", "核")
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
    # 核 must not become 覈 (s2t phrase bug)
    assert to_traditional("核") == "核"
    assert to_traditional("核心") == "核心"
    assert to_traditional("核实") == "核實"
    assert to_traditional("审核") == "審核"
    assert to_traditional("覈實") == "核實"
    assert to_traditional("覈心") == "核心"
    print("trad_chinese mou/mei + hat6 ok")
