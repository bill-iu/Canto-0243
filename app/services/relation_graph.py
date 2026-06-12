"""近反義關係圖：DB 列 + 排序 enrichment（repo 僅負責 fetch）。"""
from __future__ import annotations

from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.models.word import Word
from app.repositories.word_relation_repo import fetch_bidirectional_relations, load_db_char_set
from app.services.syn_ant_ranking import final_score, parse_group_codes


def normalize_relation_row(
    rtype: str,
    rchar: str,
    source,
    score,
    jyutping,
    code,
    group_codes_raw,
    *,
    query: str,
    db_char_set: Set[str],
) -> dict | None:
    if not rchar or rchar == query:
        return None
    in_db = rchar in db_char_set
    group_codes = parse_group_codes(group_codes_raw)
    return {
        "char": rchar,
        "relation": rtype,
        "source": source or "word_relations",
        "score": score,
        "in_db": in_db,
        "jyutping": jyutping or "",
        "code": code or "",
        "group_codes": group_codes,
        "_group_codes": group_codes,
        "_sort": final_score(source=source, confidence=score, in_db=in_db),
    }


class RelationGraph:
    """Deep module：從 word_relations 取得並 enrich 近反義列。"""

    def fetch_relations(
        self,
        db: Session,
        query: str,
        *,
        db_char_set: Optional[Set[str]] = None,
    ) -> List[dict]:
        q = query.strip()
        if not q:
            return []
        if db_char_set is None:
            db_char_set = load_db_char_set(db)

        word_ids = [w.id for w in db.query(Word.id).filter(Word.char == q).all()]
        items: List[dict] = []
        for row in fetch_bidirectional_relations(db, word_ids):
            item = normalize_relation_row(*row, query=q, db_char_set=db_char_set)
            if item:
                items.append(item)
        return items


_default_graph = RelationGraph()


def fetch_relations_for_query(
    db: Session,
    query: str,
    *,
    db_char_set: Optional[Set[str]] = None,
) -> List[dict]:
    return _default_graph.fetch_relations(db, query, db_char_set=db_char_set)
