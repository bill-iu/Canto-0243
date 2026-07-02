"""近反義池快照 DTO — 建池實作見 pool_builder.build_pool。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

DEFAULT_PAGE_SIZE = 160


@dataclass(frozen=True)
class PoolSnapshot:
    """近反義池快照：定格結果，唔綁詞條庫連線或靜態埠。"""

    query: str
    syns: List[dict]
    ants: List[dict]
    semantic: List[dict]
    rel_syn: int = 0
    rel_ant: int = 0
    rel_sem: int = 0
    static_syn: int = 0
    static_ant: int = 0

    def page(self, limit: int, offset: int) -> List[dict]:
        if limit < 0:
            limit = DEFAULT_PAGE_SIZE
        if offset < 0:
            offset = 0
        combined = self.syns + self.ants + self.semantic
        return combined[offset : offset + limit]

    def chars(self, kind: str) -> List[str]:
        if kind not in ("syn", "ant"):
            return []
        rows = self.syns if kind == "syn" else self.ants
        return [r["char"] for r in rows if r.get("char")]


from app.domain.relations.pool_builder import build_pool  # noqa: E402

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "PoolSnapshot",
    "build_pool",
]
