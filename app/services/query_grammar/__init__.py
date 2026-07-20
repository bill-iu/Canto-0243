"""查詢 grammar 家族（ADR-0046 §3）— 鏡像 client/src/db/query/grammar。

Public API: import family modules directly（equals／plus／…）。
Mirrored stems: contracts/query-grammar-families.json（C10）。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CONTRACT = (
    Path(__file__).resolve().parents[3] / "contracts" / "query-grammar-families.json"
)


@lru_cache(maxsize=1)
def mirrored_families() -> tuple[str, ...]:
    data = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    families = data.get("mirrored_families")
    if not isinstance(families, list) or not families:
        raise RuntimeError("query-grammar-families.json: mirrored_families required")
    return tuple(str(x) for x in families)


__all__ = ["mirrored_families"]
