"""搜尋模式轉接決策 — ModePolicy（結果無副作用）。

介面：plan_redirect → ModeRedirectPlan。
Detect 雙 adapter（full-parse / regex）保留於內部；案例表見
contracts/relation-syntax-detect-cases.json。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

from app.services._generated.fillword_connectives import FILLWORD_CONNECTIVES_STR

DetectKind = Literal["full", "regex"]

_COMPOUND_CONNECT_SYN_RE = re.compile(
    rf"^(\d*)~([{FILLWORD_CONNECTIVES_STR}])~([一-鿿])?$"
)
_COMPOUND_CONNECT_ANT_RE = re.compile(
    rf"^(\d*)!([{FILLWORD_CONNECTIVES_STR}])!([一-鿿])?$"
)
_COMPOUND_SYN_RE = re.compile(r"^(\d*)~~([一-鿿])?$")
_COMPOUND_ANT_RE = re.compile(r"^(\d*)!!([一-鿿])?$")
_RELATION_LOOKUP_RE = re.compile(r"^(\d*)([~!])([一-鿿]+)$")


@dataclass(frozen=True)
class ModeRedirectPlan:
    should_redirect: bool
    effective_mode: Optional[str]  # m1 | m2 | m3 when redirecting
    hint: Optional[str]
    reset_offset: bool


def _normalize_query_syntax(q: str) -> str:
    return (
        (q or "")
        .replace("＊", "*")
        .replace("﹡", "*")
        .replace("！！", "!!")
        .replace("～～", "~~")
        .replace("！", "!")
        .replace("～", "~")
        .replace("？", "?")
    )


def is_relation_syntax_regex(q: str) -> bool:
    """Regex adapter — parity with client mode-detect / frontend query-mode-detect."""
    n = _normalize_query_syntax((q or "").strip())
    if not n:
        return False
    return bool(
        _COMPOUND_CONNECT_SYN_RE.match(n)
        or _COMPOUND_CONNECT_ANT_RE.match(n)
        or _COMPOUND_SYN_RE.match(n)
        or _COMPOUND_ANT_RE.match(n)
        or _RELATION_LOOKUP_RE.match(n)
    )


def _detect_relation(q: str, detect: DetectKind) -> bool:
    if detect == "regex":
        return is_relation_syntax_regex(q)
    from app.services.query_parse import is_relation_syntax_query

    return is_relation_syntax_query(q)


def plan_redirect(
    q: str,
    *,
    current_mode: str,
    fallback_0243_mode: str | None = None,
    detect: DetectKind = "full",
    is_relation: bool | None = None,
    lang: str = "zh",
) -> ModeRedirectPlan:
    """Decide 搜尋模式轉接 — callers apply URL／hint／dispatch。

    Only when current_mode is syn and q is 近反義關係查詢語法.
    """
    from app.services.query_parse import mode_redirect_hint, resolve_fallback_0243_mode

    if current_mode != "syn":
        return ModeRedirectPlan(
            should_redirect=False,
            effective_mode=None,
            hint=None,
            reset_offset=False,
        )

    relation = (
        is_relation
        if is_relation is not None
        else _detect_relation(q, detect)
    )
    if not relation:
        return ModeRedirectPlan(
            should_redirect=False,
            effective_mode=None,
            hint=None,
            reset_offset=False,
        )

    effective = resolve_fallback_0243_mode(fallback_0243_mode)
    hint = mode_redirect_hint(effective) if lang != "en" else _hint_en(effective)
    return ModeRedirectPlan(
        should_redirect=True,
        effective_mode=effective,
        hint=hint,
        reset_offset=True,
    )


def _hint_en(mode: str) -> str:
    labels = {
        "m2": "02493 Mode (Strict)",
        "m3": "394052 Mode (Six tones)",
    }
    label = labels.get(mode, "0243 Mode (Loose)")
    return f"This syntax switched to {label} for search"


def mode_policy_self_check() -> None:
    idle = plan_redirect("~開心", current_mode="m1", detect="regex")
    assert not idle.should_redirect, idle

    go = plan_redirect(
        "~開心",
        current_mode="syn",
        fallback_0243_mode="m2",
        detect="regex",
    )
    assert go.should_redirect and go.effective_mode == "m2" and go.reset_offset
    assert go.hint and "02493" in go.hint

    pool = plan_redirect("開心", current_mode="syn", detect="regex")
    assert not pool.should_redirect

    full = plan_redirect("~~", current_mode="syn", detect="full")
    assert full.should_redirect and full.effective_mode == "m1"


__all__ = [
    "DetectKind",
    "ModeRedirectPlan",
    "is_relation_syntax_regex",
    "mode_policy_self_check",
    "plan_redirect",
]

if __name__ == "__main__":
    mode_policy_self_check()
    print("mode_policy_self_check ok")
