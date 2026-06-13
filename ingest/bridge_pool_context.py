"""Checkpoint + lean relation pools for syn-bridge ingest."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.repositories.word_relation_repo import load_db_char_set
from app.services.relation_pool_builder import RelationPoolBuilder
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT_PATH = REPO_ROOT / "data" / "locks" / "expand-antonyms-syn-bridge.checkpoint.json"


class IngestBridgePoolContext:
    """Ingest adapter: cached 收錄 membership + RelationPoolBuilder (同源於 近反義模式)."""

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
        self._builder = RelationPoolBuilder(
            db,
            thesaurus=self.thesaurus,
            membership=load_db_char_set(db),
        )

    def relation_chars(self, query: str, kind: str) -> List[str]:
        q = (query or "").strip()
        if not q or kind not in ("syn", "ant"):
            return []
        return self._builder.build(q, include_static=self.include_static).chars(kind)


def read_bridge_checkpoint(path: Path | None = None) -> Optional[dict]:
    p = path or DEFAULT_CHECKPOINT_PATH
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_bridge_checkpoint(
    *,
    offset: int,
    inserted_cumulative: int,
    total_targets: int,
    path: Path | None = None,
) -> None:
    p = path or DEFAULT_CHECKPOINT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "offset": int(offset),
        "inserted_cumulative": int(inserted_cumulative),
        "total_targets": int(total_targets),
        "updated_at": int(time.time()),
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_bridge_checkpoint(path: Path | None = None) -> None:
    p = path or DEFAULT_CHECKPOINT_PATH
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
