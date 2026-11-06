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

# s2hk can re-convert already-traditional phrases on a second ingest pass.
# Restore whole lexical contexts only; 幹部、徵求、鬥爭 and 幾何 keep their senses.
_CONTEXTUAL_RESTORE: dict[str, str] = {
    "長徵": "長征",
    "親徵": "親征",
    "東徵": "東征",
    "幹係": "干係",
    "幹擾": "干擾",
    "抗幹擾": "抗干擾",
    "幹擾素": "干擾素",
    "幹預": "干預",
    "鬥轉星移": "斗轉星移",
    "窗明幾淨": "窗明几淨",
    "子醜寅卯": "子丑寅卯",
    "裏長": "里長",
    "慄鈣土": "栗鈣土",
    "同裏": "同里",
    "徵闢": "徵辟",
    "報名錶": "報名表",
    "頭麪人物": "頭面人物",
    "劃手": "划手",
    "機械繫": "機械系",
    "幹擾機": "干擾機",
    "鬥式": "斗式",
}

# Bare word senses: ocean surface and literary richness/fragrance. Preserve the
# input literal, not its converted output (洋麵 and 鬱鬱 have different senses).
_PRESERVE_LITERALS = frozenset({"洋面", "郁郁"})


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
    if text in _PRESERVE_LITERALS:
        return text
    converter = _s2hk_converter()
    out = converter.convert(text) if converter is not None else text
    # ponytail: without OpenCC, still collapse 覈→核 (HKVariants); ceiling = rare literary 覈
    out = out.replace("覈", "核")
    for bad, good in _MOU_FORTUNE_RESTORE:
        out = out.replace(bad, good)
    # Exact literals: compound relation keys need their own reviewed migration.
    return _CONTEXTUAL_RESTORE.get(out, out)


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
