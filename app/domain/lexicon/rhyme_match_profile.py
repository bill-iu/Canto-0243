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

TONG_GROUPS: tuple[tuple[str, ...], ...] = (
    ("i", "ei", "yu", "eoi", "ai"),
    ("oeng", "on", "ong"),
    ("an", "am", "ang"),
    ("aa",),
    ("in", "im", "yun"),
    ("ing",),
    ("eng",),
    ("aam", "aan", "aang"),
    ("ung",),
    ("oi", "ui"),
    ("aai",),
    ("iu",),
    ("ou", "u"),
    ("o",),
    ("au",),
    ("aau",),
    ("e",),
    ("eon",),
    ("un",),
    ("oe",),
    ("aa", "aap", "aat", "aak"),
    ("a", "ap", "at", "ak"),
    ("e", "ek", "ep", "et", "em", "en", "eng"),
    ("i", "ip", "it", "ik", "im", "in", "ing"),
    ("o", "ok", "ot", "op", "on", "ong", "oi"),
    ("oe", "oek", "oet", "oeng", "eot", "eon", "eoi"),
    ("u", "ut", "uk", "un", "ung", "ou"),
    ("yu", "yut", "yun"),
    ("m", "ng"),
    ("eu",),
)

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
