# ==================== 粵語聲母韻母對照表 ====================
# 這是一個獨立的 guideline 表，以後可以持續擴充

JYUTPING_TABLE = {
    # 聲母 (Initials) - 包含複聲母
    "initials": [
        "ng", "gw", "kw", "zy", "cy", "sy",   # 複聲母
        "b", "p", "m", "f", "d", "t", "n", "l",
        "g", "k", "h", "j", "w", "z", "c", "s"
    ],

    # 韻母 (Finals) - 不含聲調
    "finals": [
        "a", "aa", "ai", "aai", "au", "aau", "am", "aam", "an", "aan", "ang", "aang", "ap", "aap", "at", "aat", "ak", "aak",
        "e", "ei", "eu", "em", "eng", "ep", "ek",
        "i", "iu", "im", "in", "ing", "ip", "it", "ik",
        "o", "oi", "ou", "on", "ong", "ot", "ok",
        "u", "ui", "un", "ung", "ut", "uk",
        "yu", "yun", "yut",
        # 可繼續新增
    ]
}

# 特殊對應（唯二你提到的情況 + 常見例外）
SPECIAL_CASES = {
    "m4": ("m", "", 4),
    "m5": ("m", "", 5),
    "ng5": ("ng", "", 5),
    "ng4": ("ng", "", 4),
    "ng6": ("ng", "", 6),
    # 以後可以繼續新增其他特殊情況
}