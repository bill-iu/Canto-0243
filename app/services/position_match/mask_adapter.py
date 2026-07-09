"""缺字 mask 比對 — 只讀 MatchSpec／mask 字串（執行期自含）。"""
from __future__ import annotations

from typing import Optional

from app.services.position_match.spec import MatchSpec
from app.services.query_tokens import is_wildcard_char


def matches_mask_literal_chars(word_char: str, mask: str) -> bool:
    """非通配、非碼槽之 mask 格須與字面一致。"""
    if len(word_char) != len(mask):
        return False
    for idx, ch in enumerate(mask):
        if is_wildcard_char(ch) or ch.isdigit():
            continue
        if word_char[idx] != ch:
            return False
    return True


def mask_char_glob_pattern(mask: str) -> str:
    """SQLite GLOB：通配／碼槽 → ?，字面保留。"""
    return "".join(
        "?" if (is_wildcard_char(ch) or ch.isdigit()) else ch
        for ch in mask
    )


def mask_fixed_literal_prefix(mask: str) -> str:
    """首段連續字面（至第一個通配或碼槽）。"""
    prefix: list[str] = []
    for ch in mask:
        if is_wildcard_char(ch) or ch.isdigit():
            break
        prefix.append(ch)
    return "".join(prefix)


def required_codes_from_spec(spec: MatchSpec) -> list[Optional[str]]:
    """執行期碼槽：mask 內 digit + spec.slots code_digit（slot 覆寫）。

    PR-A：唔讀 spec.code_prefix（全碼 hint 唔再驅動比對；見 ADR-0028）。
    """
    codes: list[Optional[str]] = [None] * spec.width
    mask = spec.mask or ""
    if len(mask) == spec.width:
        for idx, ch in enumerate(mask):
            if ch.isdigit():
                codes[idx] = ch
    for slot in spec.slots:
        if slot.kind == "code_digit" and 0 <= slot.pos < spec.width:
            codes[slot.pos] = str(slot.value) if slot.value is not None else None
    return codes


def dense_code_from_required(required: list[Optional[str]]) -> Optional[str]:
    """每位皆有單一 digit 時合成全碼，供 dense SQL IN + get_code_variants 笛卡爾。"""
    if not required:
        return None
    parts: list[str] = []
    for d in required:
        if d is None or not str(d).isdigit() or len(str(d)) != 1:
            return None
        parts.append(str(d))
    return "".join(parts) if parts else None


def dense_code_from_spec(spec: MatchSpec) -> Optional[str]:
    """MatchSpec → dense 全碼（只 slots／mask；唔用 code_prefix）。"""
    return dense_code_from_required(required_codes_from_spec(spec))


def required_codes_from_digit_string(digits: str) -> list[Optional[str]]:
    """短碼前綴字串 → 逐格 required（compound／近反義種子）。"""
    if not digits or not str(digits).isdigit():
        return []
    return [ch for ch in str(digits)]
