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
    "白麪書生": "白面書生",
    "鬥門": "斗門",
    "車鬥": "車斗",
    "傢俱城": "家具城",
    "徵南將軍": "征南將軍",
    "幹擾源": "干擾源",
    "條幾": "條几",
    "抗幹擾性": "抗干擾性",
    "能徵慣戰": "能征慣戰",
    "毒血癥": "毒血症",
    "儀錶板": "儀表板",
    "記裏鼓車": "記里鼓車",
    "數鬥": "數斗",
    "風鬥": "風斗",
    "劃得來": "划得來",
    "醫託": "醫托",
    "無精打採": "無精打采",
    "離題萬裏": "離題萬里",
    "前程萬裏": "前程萬里",
    "基託": "基托",
    "日進鬥金": "日進斗金",
    "星移鬥轉": "星移斗轉",
    "沒精打採": "沒精打采",
    "烘雲託月": "烘雲托月",
    "鄉願": "鄉愿",
    "錐慄": "錐栗",
    "剷鬥": "剷斗",
    "抓鬥": "抓斗",
    "翻鬥": "翻斗",
    "開夥": "開伙",
    "幹擾能力": "干擾能力",
    "有徵無戰": "有征無戰",
    "並條機": "併條機",
    "遊離鈣": "游離鈣",
    "釜底遊魚": "釜底游魚",
    "一手託天": "一手托天",
    "一瀉萬裏": "一瀉萬里",
    "一舉萬裏": "一舉萬里",
    "醜時": "丑時",
    "幹雲蔽日": "干雲蔽日",
    "二週目": "二周目",
    "交流乾擾": "交流干擾",
    "人工幹預": "人工干預",
    "劃不來": "划不來",
    "前僕後繼": "前仆後繼",
    "剋制不住": "克制不住",
    "屢僕屢起": "屢仆屢起",
    "幹擾力": "干擾力",
    "幹擾哨聲": "干擾哨聲",
    "幹擾器": "干擾器",
    "幹礙": "干礙",
    "幹連": "干連",
    "御駕親徵": "御駕親征",
    "復闢事件": "復辟事件",
    "手製動": "手制動",
    "手製動器": "手制動器",
    "排除幹擾": "排除干擾",
    "掛鬥": "掛斗",
    "據雲": "據云",
    "早佔勿藥": "早占勿藥",
    "星佔學": "星占學",
    "星佔術": "星占術",
    "木傢俱": "木家具",
    "木製傢俱": "木製家具",
    "木託盤": "木托盤",
    "機械繫統": "機械系統",
    "水煙鬥": "水煙斗",
    "煙鬥": "煙斗",
    "準建證": "准建證",
    "準遷證": "准遷證",
    "濾鬥": "濾斗",
    "煙鬥架": "煙斗架",
    "煙鬥絲": "煙斗絲",
    "直麪人生": "直面人生",
    "相隔萬裏": "相隔萬里",
    "移星換鬥": "移星換斗",
    "礙難照準": "礙難照准",
    "續藉手續": "續借手續",
    "能徵善戰": "能征善戰",
    "舉手錶決": "舉手表決",
    "萬貫傢俬": "萬貫家私",
    "葉麪肥": "葉面肥",
}

# Bare word senses: preserve the input, since the converted form can have its
# own valid sense (e.g. 斗車 is a hopper cart; 鬥車 means racing cars).
_PRESERVE_LITERALS = {
    "洋面": "洋面", "郁郁": "郁郁", "斗車": "斗車", "斗车": "斗車",
    # Rowing contexts keep 划; already-traditional 劃動/劃進 retain their own sense.
    "划動": "划動", "划动": "划動",
    "划進": "划進", "划进": "划進",
    "划進來": "划進來", "划进来": "划進來",
    "划進去": "划進去", "划进去": "划進去",
    "划過來": "划過來", "划过来": "划過來",
    "划過去": "划過去", "划过去": "划過去",
    # Swimming motion keeps 游; travel expressions written 遊 stay distinct.
    "游來": "游來", "游来": "游來",
    "游來游去": "游來游去", "游来游去": "游來游去",
    "游進去": "游進去", "游进去": "游進去",
    "游過來": "游過來", "游过来": "游過來",
    "游過去": "游過去", "游过去": "游過去",
    "潛游": "潛游", "潜游": "潛游",
}


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
        return _PRESERVE_LITERALS[text]
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
