"""Ingest adapter: cached 收錄 membership + build_pool（同源於 近反義模式）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.relations.pool import build_pool
from app.repositories.word_relation_repo import load_db_char_set
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE_CHECKPOINT = REPO_ROOT / "data" / "locks" / "expand-antonyms-syn-bridge.checkpoint.json"


class IngestBridgePoolContext:
    def __init__(
        self,
        db: Session,
        *,
        include_static: bool = True,
        thesaurus: Optional[ThesaurusPort] = None,
    ) -> None:
        self.db = db
        self.include_static = include_static
        self.thesaurus = thesaurus or default_thesaurus_port()
        self._membership = load_db_char_set(db)

    def relation_chars(self, query: str, kind: str) -> List[str]:
        q = (query or "").strip()
        if not q or kind not in ("syn", "ant"):
            return []
        return build_pool(
            self.db,
            q,
            include_static=self.include_static,
            thesaurus=self.thesaurus,
            membership=self._membership,
            quiet=True,
        ).chars(kind)


def read_bridge_checkpoint(path: Path | None = None) -> dict | None:
    p = path or DEFAULT_BRIDGE_CHECKPOINT
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def write_bridge_checkpoint(
    *,
    offset: int,
    inserted_cumulative: int,
    total_targets: int,
    path: Path | None = None,
) -> None:
    p = path or DEFAULT_BRIDGE_CHECKPOINT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "offset": int(offset),
                "inserted_cumulative": int(inserted_cumulative),
                "total_targets": int(total_targets),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def clear_bridge_checkpoint(path: Path | None = None) -> None:
    p = path or DEFAULT_BRIDGE_CHECKPOINT
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
