"""Ingest adapter: cached 收錄 membership + build_pool（同源於 近反義模式）。"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.relations.pool import build_pool
from app.repositories.word_relation_repo import load_db_char_set
from app.services.thesaurus_port import ThesaurusPort, default_thesaurus_port


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
