"""Char-level 關係圖：直接近義鄰居與 ! 鏡射對（runtime + ingest 同源）。"""

from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

from sqlalchemy.orm import Session, aliased

from app.models.word import Word, WordRelation
from app.repositories.word_relation_repo import load_db_char_set
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port

ANT_SYN_MIRROR_SOURCE = "ant_syn_mirror"


class CharRelationGraph:
    """Bidirectional char syn adjacency + ant mirror pair collection."""

    def __init__(
        self,
        db: Session,
        thesaurus: ThesaurusPort,
        *,
        membership: Optional[Set[str]] = None,
    ) -> None:
        self._db = db
        self._thesaurus = thesaurus
        self._membership = membership
        self._adjacency: Optional[Dict[str, Set[str]]] = None

    def _resolve_membership(self) -> Set[str]:
        if self._membership is not None:
            return self._membership
        return load_db_char_set(self._db)

    def _build_adjacency(self, *, include_static: bool) -> Dict[str, Set[str]]:
        adj: Dict[str, Set[str]] = {}
        w1 = aliased(Word)
        w2 = aliased(Word)
        for a, b in (
            self._db.query(w1.char, w2.char)
            .join(WordRelation, WordRelation.word_id == w1.id)
            .join(w2, WordRelation.related_id == w2.id)
            .filter(WordRelation.relation_type == "syn")
            .all()
        ):
            if not a or not b or a == b:
                continue
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

        if include_static:
            present = self._resolve_membership()
            self._thesaurus.ensure_loaded()
            for ch in present:
                for syn in self._thesaurus.get_synonyms(ch):
                    if not syn or syn == ch or syn not in present:
                        continue
                    adj.setdefault(ch, set()).add(syn)
                    adj.setdefault(syn, set()).add(ch)

        return adj

    def _ensure_adjacency(self, *, include_static: bool) -> Dict[str, Set[str]]:
        if self._adjacency is None:
            self._adjacency = self._build_adjacency(include_static=include_static)
        return self._adjacency

    def direct_syn_neighbors(self, char: str, *, include_static: bool = True) -> Set[str]:
        """直接近義鄰居：DB 雙向 syn + ThesaurusPort 靜態近義（在 membership 內）。"""
        ch = (char or "").strip()
        if not ch:
            return set()
        adj = self._ensure_adjacency(include_static=include_static)
        return set(adj.get(ch, set()))

    def _direct_ant_oriented_pairs(
        self,
        *,
        exclude_sources: Optional[Set[str]] = None,
    ) -> Set[Tuple[str, str]]:
        exclude_sources = exclude_sources or set()
        w1 = aliased(Word)
        w2 = aliased(Word)
        oriented: Set[Tuple[str, str]] = set()
        for a, b, src in (
            self._db.query(w1.char, w2.char, WordRelation.source)
            .join(WordRelation, WordRelation.word_id == w1.id)
            .join(w2, WordRelation.related_id == w2.id)
            .filter(WordRelation.relation_type == "ant")
            .all()
        ):
            if not a or not b or a == b:
                continue
            if src in exclude_sources:
                continue
            oriented.add((a, b))
            oriented.add((b, a))
        return oriented

    def collect_mirror_ant_pairs(
        self,
        *,
        include_static: bool = True,
        exclude_sources: Optional[Set[str]] = None,
    ) -> Set[Tuple[str, str]]:
        """Char pairs (head, tail) for ! 鏡射：ant endpoint + 其直接近義鄰居。"""
        exclude_sources = exclude_sources or {ANT_SYN_MIRROR_SOURCE}
        adj = self._ensure_adjacency(include_static=include_static)
        seeds = self._direct_ant_oriented_pairs(exclude_sources=exclude_sources)
        pairs: Set[Tuple[str, str]] = set()
        for head, endpoint in seeds:
            if head == endpoint:
                continue
            pairs.add((head, endpoint))
            for syn_char in adj.get(endpoint, set()):
                if syn_char and syn_char != head:
                    pairs.add((head, syn_char))
        return pairs

    def direct_ant_oriented_pairs(
        self,
        *,
        exclude_sources: Optional[Set[str]] = None,
    ) -> Set[Tuple[str, str]]:
        return self._direct_ant_oriented_pairs(exclude_sources=exclude_sources)


def default_char_relation_graph(
    db: Session,
    *,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
) -> CharRelationGraph:
    return CharRelationGraph(
        db,
        thesaurus or default_thesaurus_port(),
        membership=membership,
    )


__all__ = [
    "ANT_SYN_MIRROR_SOURCE",
    "CharRelationGraph",
    "default_char_relation_graph",
]
