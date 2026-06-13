"""Checkpoint + lean relation pools for syn-bridge ingest."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.repositories.word_relation_repo import load_db_char_set
from app.services.syn_ant_ranking import merge_relation_pools, sort_ant_pool, sort_syn_pool
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT_PATH = REPO_ROOT / "data" / "locks" / "expand-antonyms-syn-bridge.checkpoint.json"


class IngestBridgePoolContext:
    """Cached db_char_set + thesaurus; same syn/ant sources as runtime ~ without per-call rank()."""

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
        self.db_char_set: Set[str] = load_db_char_set(db)

    def relation_chars(self, query: str, kind: str) -> List[str]:
        from app.services.relation_ranker import (
            _load_static_pools,
            _resolve_morpheme_chars,
            _static_relation_pool,
        )
        from app.services.syn_ant_service import fetch_relations

        q = (query or "").strip()
        if not q:
            return []

        rel_items = fetch_relations(self.db, q, db_char_set=self.db_char_set)
        static_syns: List[str] = []
        static_ants: List[str] = []
        if self.include_static:
            static_syns, static_ants = _load_static_pools(q, self.thesaurus)

        morpheme_chars = _resolve_morpheme_chars(q, static_syns, static_ants, self.thesaurus)
        effective_morphemes = morpheme_chars if len(q) >= 2 else set()

        if kind == "syn":
            db_pool = [i for i in rel_items if i["relation"] == "syn"]
            static_pool = _static_relation_pool("syn", static_syns, self.db_char_set)
            pool = sort_syn_pool(
                q,
                list(merge_relation_pools(db_pool, static_pool).values()),
                effective_morphemes,
            )
        elif kind == "ant":
            db_pool = [i for i in rel_items if i["relation"] == "ant"]
            static_pool = _static_relation_pool("ant", static_ants, self.db_char_set)
            pool = sort_ant_pool(
                q,
                list(merge_relation_pools(db_pool, static_pool).values()),
                effective_morphemes,
            )
        else:
            return []

        out: List[str] = []
        seen: Set[str] = set()
        for item in pool:
            ch = item.get("char") or ""
            if not ch or ch == q or ch in seen:
                continue
            seen.add(ch)
            out.append(ch)
        return out


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
