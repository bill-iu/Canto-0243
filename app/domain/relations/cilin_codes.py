"""Cilin leaf / hierarchy codes — shared by ingest storage and ranking (ADR-0039 GC1)."""
from __future__ import annotations

import re
from typing import List

# Leaf synonym code: Aa01A01=, Ca01B01=, etc.
CILIN_LEAF_CODE_RE = re.compile(r"^[A-Z][a-z]\d{2}[A-Z]\d{2}=$")


def is_cilin_leaf_code(code: str) -> bool:
    return bool(CILIN_LEAF_CODE_RE.match(code or ""))


def leaf_code_to_hierarchy_codes(leaf_code: str) -> List[str]:
    """Expand leaf code into ancestor codes (A → … → leaf)."""
    code = (leaf_code or "").strip()
    if not code:
        return []
    m = re.match(r"^([A-Z])([a-z])(\d{2})([A-Z])(\d{2})=$", code)
    if not m:
        return [code]
    a, b, d, e, f = m.groups()
    return [a, a + b, a + b + d, a + b + d + e, a + b + d + e + f + "="]


def expand_group_codes_field(raw: object) -> List[str]:
    """
    Storage may be:
    - JSON array (legacy full hierarchy)
    - leaf code string only (ADR-0039 GC1)
    - already a list
    """
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(c) for c in raw if c]
    if not isinstance(raw, str):
        return []
    s = raw.strip()
    if not s:
        return []
    if s[0] == "[":
        import json

        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(c) for c in parsed if c]
        except (json.JSONDecodeError, TypeError):
            return [s]
        return []
    if is_cilin_leaf_code(s):
        return leaf_code_to_hierarchy_codes(s)
    return [s]


__all__ = [
    "CILIN_LEAF_CODE_RE",
    "expand_group_codes_field",
    "is_cilin_leaf_code",
    "leaf_code_to_hierarchy_codes",
]
