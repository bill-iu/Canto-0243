"""韻母比對檔 — expand tables (ADR-0078). Port of shared/rhyme-match-profile.mjs."""
from __future__ import annotations

from typing import Iterable, Optional

RHYME_PROFILES = ("exact", "tong", "nucleus", "coda")

RHYME_PROFILE_LABELS = {
    "exact": "正韻",
    "tong": "通韻",
    "nucleus": "腹韻",
    "coda": "尾韻",
}

# 通韻：部／韻名 + 舒入相配（rhyme2 舒聲結構 + rhyme.txt 入聲歸部）
TONG_CLASSES: tuple[dict, ...] = (
    {"name": "依時部", "finals": ("i", "yu", "eoi", "ei", "ip", "it", "ik", "yut", "eot")},
    {"name": "郎當部", "finals": ("ong", "on", "oeng", "ok", "ot", "oek")},
    {"name": "民親部", "finals": ("an", "ang", "am", "at", "ak", "ap")},
    {"name": "田邊部", "finals": ("in", "im", "yun", "it", "ip", "yut")},
    {"name": "欄柵部", "finals": ("aan", "aam", "aang", "aat", "aap", "aak")},
    {"name": "勞高部", "finals": ("ou", "u", "uk", "ut")},
    {"name": "裁開部", "finals": ("oi", "ui")},
    {"name": "雞啼韻", "finals": ("ai",)},
    {"name": "倫敦韻", "finals": ("eon", "eot")},
    {"name": "盤歡韻", "finals": ("un", "ut")},
    {"name": "埋街韻", "finals": ("aai",)},
    {"name": "英明韻", "finals": ("ing", "ik")},
    {"name": "靈釘韻", "finals": ("eng", "ek")},
    {"name": "優遊韻", "finals": ("au",)},
    {"name": "農工韻", "finals": ("ung", "uk")},
    {"name": "逍遙韻", "finals": ("iu",)},
    {"name": "羅疏韻", "finals": ("o", "ok", "ot", "op")},
    {"name": "麻花韻", "finals": ("aa", "aap", "aat", "aak")},
    {"name": "咆哮韻", "finals": ("aau",)},
    {"name": "斜遮韻", "finals": ("e", "ep", "et", "ek", "em", "en")},
    {"name": "靴瘸韻", "finals": ("oe", "oek", "oet")},
    {"name": "五唔韻", "finals": ("m", "ng")},
    {"name": "掉韻", "finals": ("eu",)},
)

TONG_GROUPS: tuple[tuple[str, ...], ...] = tuple(c["finals"] for c in TONG_CLASSES)

NUCLEUS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("aai",),
    ("aau",),
    ("aa", "aap", "aat", "aak", "aam", "aan", "aang"),
    ("ai",),
    ("au",),
    ("ei",),
    ("eu",),
    ("iu",),
    ("ou",),
    ("oe", "oek", "oet", "oeng"),
    ("eot", "eon", "eoi"),
    ("ui",),
    ("ng",),
    ("yu", "yut", "yun"),
    ("ap", "at", "ak", "am", "an", "ang", "a"),
    ("e", "ek", "eng", "em", "en", "ep", "et"),
    ("i", "ip", "it", "ik", "im", "in", "ing"),
    ("o", "ot", "ok", "on", "ong", "oi", "op"),
    ("u", "ut", "uk", "un", "ung"),
    ("m",),
)

CODA_GROUPS: tuple[tuple[str, ...], ...] = (
    ("i",),
    ("ip", "ap", "aap", "ep", "op"),
    ("it", "yut", "ut", "eot", "oet", "ot", "at", "aat", "et"),
    ("ik", "uk", "ek", "oek", "ok", "ak", "aak"),
    ("im", "am", "aam", "m", "em"),
    ("in", "yun", "un", "eon", "on", "an", "aan", "en"),
    ("ing", "ung", "eng", "oeng", "ong", "ang", "aang", "ng"),
    ("iu", "ou", "au", "aau", "eu"),
    ("yu",),
    ("ui", "ei", "eoi", "oi", "ai", "aai"),
    ("e",),
    ("oe",),
    ("o",),
    ("aa", "a"),
    ("u",),
)


def _build_lookup(groups: tuple[tuple[str, ...], ...]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for group in groups:
        s = set(group)
        for f in group:
            if f in out:
                out[f] |= s
            else:
                out[f] = set(s)
    return out


_TONG = _build_lookup(TONG_GROUPS)
_NUCLEUS = _build_lookup(NUCLEUS_GROUPS)
_CODA = _build_lookup(CODA_GROUPS)


def is_rhyme_profile(value: object) -> bool:
    return value in RHYME_PROFILES


def normalize_rhyme_profile(value: object) -> str:
    return value if is_rhyme_profile(value) else "exact"


def _lookup(profile: str) -> Optional[dict[str, set[str]]]:
    if profile == "tong":
        return _TONG
    if profile == "nucleus":
        return _NUCLEUS
    if profile == "coda":
        return _CODA
    return None


def expand_one_final(final: str, profile: str = "exact") -> set[str]:
    f = (final or "").lower().strip()
    if not f:
        return set()
    p = normalize_rhyme_profile(profile)
    if p == "exact":
        return {f}
    table = _lookup(p)
    if table and f in table:
        return set(table[f])
    return {f}


def expand_final_options(options: Iterable[str] | None, profile: str = "exact") -> set[str]:
    p = normalize_rhyme_profile(profile)
    if not options:
        return set()
    if p == "exact":
        return {str(x).lower() for x in options if x}
    out: set[str] = set()
    for f in options:
        out |= expand_one_final(str(f), p)
    return out


def finals_compatible(a: str, b: str, profile: str = "exact") -> bool:
    fa = (a or "").lower()
    fb = (b or "").lower()
    if not fa or not fb:
        return False
    if normalize_rhyme_profile(profile) == "exact":
        return fa == fb
    return fb in expand_one_final(fa, profile)
