"""Pure 394052／0243 digit-slot match helpers (no services deps).

Used by domain (reference_reading) and position_match filters.
"""
from __future__ import annotations

from typing import Optional

from app.utils.jyutping_codec import get_code_variants


def matches_code_positions(
    code_str: str, required_codes: list[Optional[str]], mode: str
) -> bool:
    """逐格 digit 鬆檔比對。required 可短於 code（前綴）；None 格跳過。"""
    if not required_codes:
        return True
    if not code_str and any(r is not None for r in required_codes):
        return False
    for idx, req_digit in enumerate(required_codes):
        if req_digit is None:
            continue
        if idx >= len(code_str):
            return False
        if code_str[idx] not in set(get_code_variants(str(req_digit), mode)):
            return False
    return True


def required_codes_from_digit_string(digits: str) -> list[Optional[str]]:
    """短碼前綴字串 → 逐格 required（compound／近反義種子／等號左碼）。"""
    if not digits or not str(digits).isdigit():
        return []
    return [ch for ch in str(digits)]


__all__ = [
    "matches_code_positions",
    "required_codes_from_digit_string",
]
