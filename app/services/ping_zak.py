"""平仄串列查詢 — tone-class pattern matching (CONTEXT § 平仄串列查詢)."""
from __future__ import annotations

import re
from typing import Literal

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
    "apply_ping_ze_slots",
    "code_matches_ping_ze_pattern",
    "digit_slot_matches",
    "is_ping_ze_serial_query",
    "normalize_ping_ze_pattern",
    "normalize_pzmode",
    "ping_zak_class",
    "slot_label",
    "to_match_spec",
    "try_parse_ping_ze_serial",
]


def apply_ping_ze_slots(spec, raw_q: str) -> None:
    """Overlay P/Z tone_class slots onto an existing MatchSpec (base query)."""
    from app.services.position_match import SlotConstraint

    code_digit_positions = {slot.pos for slot in spec.slots if slot.kind == "code_digit"}
    fixed_positions = {
        slot.pos
        for slot in spec.slots
        if slot.kind not in ("code_digit", "tone_class") and slot.pos not in code_digit_positions
    }
    code_positions = [pos for pos in range(spec.width) if pos not in fixed_positions]
    tokens = [token for token in raw_q if token in "PZ?" or token.isdigit()]
    for index, token in enumerate(tokens):
        if token not in "PZ" or index >= len(code_positions):
            continue
        pos = code_positions[index]
        spec.slots = [slot for slot in spec.slots if not (slot.pos == pos and slot.kind == "code_digit")]
        spec.mask = spec.mask[:pos] + "?" + spec.mask[pos + 1 :]
        spec.slots.append(
            SlotConstraint(pos=pos, kind="tone_class", value="ping" if token == "P" else "ze")
        )


def to_match_spec(parsed):
    """PingZeSerialQuery → MatchSpec (plain serial, rhyme anchor, or base overlay)."""
    from app.services.position_match import MatchSpec, SlotConstraint
    from app.services.query_types import PingZeSerialQuery

    if not isinstance(parsed, PingZeSerialQuery):
        return None
    if parsed.base is not None:
        # Lazy import: registry ↔ ping_zak cycle otherwise
        from app.services.query_match_spec_registry import build_match_spec_for_parsed

        spec = build_match_spec_for_parsed(parsed.base)
        if spec is None:
            return None
        spec.extra["code_mode"] = parsed.pzmode
        apply_ping_ze_slots(spec, parsed.raw_q)
        return spec
    spec = MatchSpec(width=len(parsed.raw_q), mask="?" * len(parsed.raw_q))
    spec.extra["code_mode"] = parsed.pzmode
    for pos, token in enumerate(parsed.raw_q):
        if token == "P":
            spec.slots.append(SlotConstraint(pos=pos, kind="tone_class", value="ping"))
        elif token == "Z":
            spec.slots.append(SlotConstraint(pos=pos, kind="tone_class", value="ze"))
        elif token.isdigit():
            spec.slots.append(SlotConstraint(pos=pos, kind="code_digit", value=token))
    if parsed.anchor:
        spec.width += 1
        spec.mask = "?" * spec.width
        spec.slots.append(
            SlotConstraint(pos=len(parsed.raw_q), kind="final_anchor", value=parsed.anchor)
        )
    return spec
