"""平仄串列查詢 — tone-class pattern matching (CONTEXT § 平仄串列查詢)."""
from __future__ import annotations

import re
from typing import Literal, Optional

from app.utils.jyutping_codec import M02493_TO_0243, normalize_02493_code

PingZak = Literal["ping", "ze"]

VALID_PZ_MODES = frozenset({"m1", "m2", "m3"})

PING_ZE_INVALID_HINT = (
    "平仄串列查詢只接受 P（平）、Z（仄）與聲調數字 0–9；"
    "字面請改用缺字語法（如 ?+就=）。"
)

_PING_ZE_SLOT_RE = re.compile(r"^[PZ0-9?]+$")
_HAS_PZ_RE = re.compile(r"[PZ]")


def ping_zak_class(code_digit: str) -> PingZak:
    """v1: 0243 碼位 → 平／仄；六聲模式就緒後可擴展。"""
    return "ping" if code_digit in ("0", "3") else "ze"


def normalize_ping_ze_pattern(q: str) -> str:
    return q.upper()


def normalize_pzmode(mode: str | None) -> str:
    return mode if mode in VALID_PZ_MODES else "m1"


def ping_ze_mode_redirect_hint(effective: str, *, lang: str = "zh") -> Optional[str]:
    """394052 就緒後轉該檔時唔出提示（Q9 修正）。"""
    return None
    if lang == "en":
        return "Ping–ze serial query switched to 02493 Mode (Strict)"
    return "平仄串列查詢已切換至 02493模式（緊）"


def digit_slot_matches(query_digit: str, code_digit: str, pzmode: str = "m1") -> bool:
    from app.utils.jyutping_codec import get_code_variants

    return code_digit in get_code_variants(query_digit, normalize_pzmode(pzmode))


def code_matches_ping_ze_pattern(code: str, pattern: str, pzmode: str = "m1") -> bool:
    pat = normalize_ping_ze_pattern(pattern)
    if len(code) != len(pat):
        return False
    for cd, slot in zip(code, pat):
        if slot == "P":
            if ping_zak_class(cd) != "ping":
                return False
        elif slot == "Z":
            if ping_zak_class(cd) != "ze":
                return False
        elif slot.isdigit():
            if not digit_slot_matches(slot, cd, pzmode):
                return False
        elif slot == "?":
            continue
        else:
            return False
    return True


def try_parse_ping_ze_serial(q: str, pzmode: str | None = None):
    """Return PingZeSerialQuery, UnmatchedQuery, or None (not a ping-ze attempt)."""
    from app.services.query_types import PingZeSerialQuery, UnmatchedQuery

    if not q or not _HAS_PZ_RE.search(q):
        return None
    if not _PING_ZE_SLOT_RE.match(q):
        return UnmatchedQuery(raw_q=q, hint=PING_ZE_INVALID_HINT)
    return PingZeSerialQuery(raw_q=normalize_ping_ze_pattern(q), pzmode=normalize_pzmode(pzmode))


def is_ping_ze_serial_query(q: str) -> bool:
    from app.services.query_types import PingZeSerialQuery

    parsed = try_parse_ping_ze_serial(q)
    return isinstance(parsed, PingZeSerialQuery)


def slot_label(slot: str, *, lang: str = "zh") -> str:
    if slot == "P":
        return "平" if lang == "zh" else "ping (P)"
    if slot == "Z":
        return "仄" if lang == "zh" else "ze (Z)"
    mapped = M02493_TO_0243.get(slot, slot)
    if lang == "zh":
        return f"與 {slot} 同音" + (f"（→{mapped}）" if mapped != slot else "")
    return f"same tone as {slot}" + (f" (→{mapped})" if mapped != slot else "")


__all__ = [
    "PING_ZE_INVALID_HINT",
    "code_matches_ping_ze_pattern",
    "digit_slot_matches",
    "is_ping_ze_serial_query",
    "normalize_ping_ze_pattern",
    "normalize_pzmode",
    "ping_zak_class",
    "slot_label",
    "try_parse_ping_ze_serial",
]
