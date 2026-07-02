"""反義端點鏡射 — per-head 字面對核心（CONTEXT § 反義端點鏡射）。"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.cilin_derived import direct_ant_seeds_for_head
from app.domain.relations.graph import CharRelationGraph, get_process_cached_graph
from app.domain.relations.valid_term import normalize_literal
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port
from app.repositories.word_relation_repo import load_db_char_set

MIRROR_SOURCE = "ant_syn_mirror"
MIRROR_CONFIDENCE = 0.72

_HANZI = re.compile(r"[\u4e00-\u9fff]")


def mirror_ant_pairs(
    head: str,
    ant_seeds: Iterable[str],
    *,
    syn_neighbors_of: Callable[[str], Iterable[str]],
    membership: Set[str],
) -> List[Tuple[str, str]]:
    """Per-head 反義端點鏡射：(head, syn_neighbor(ant_seed))，收錄閘 + 去重。"""
    h = (head or "").strip()
    if not h:
        return []
    out: List[Tuple[str, str]] = []
    seen_tails: Set[str] = {h}
    for seed in ant_seeds:
        seed = (seed or "").strip()
        if not seed:
            continue
        for syn in syn_neighbors_of(seed):
            tail = normalize_literal(syn)
            if not tail or tail == h or tail in seen_tails or tail not in membership:
                continue
            seen_tails.add(tail)
            out.append((h, tail))
    return out


def collect_lexicon_mirror_pairs(
    db: Session,
    thesaurus: ThesaurusPort,
    membership: Optional[Set[str]] = None,
    *,
    include_static: bool = True,
    graph: Optional[CharRelationGraph] = None,
) -> List[Tuple[str, str]]:
    """Bake adapter：逐收錄 head 呼叫同一 per-head 核心。"""
    lexicon = membership if membership is not None else load_db_char_set(db)
    if not lexicon:
        return []
    g = graph or get_process_cached_graph(db, thesaurus, membership=lexicon)

    def syn_fn(seed: str) -> List[str]:
        return list(g.direct_syn_neighbors(seed, include_static=include_static))

    pairs: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for head in sorted(lexicon):
        if not _HANZI.search(head):
            continue
        seeds = direct_ant_seeds_for_head(
            db,
            head,
            thesaurus=thesaurus,
            membership=lexicon,
            include_static=include_static,
        )
        for pair in mirror_ant_pairs(
            head,
            seeds,
            syn_neighbors_of=syn_fn,
            membership=lexicon,
        ):
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def write_mirror_ant_pairs_tsv(
    path: Path | str,
    pairs: Iterable[Tuple[str, str]],
    *,
    confidence: float = MIRROR_CONFIDENCE,
) -> int:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = list(pairs)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["head", "tail", "relation_type", "score"])
        for head, tail in rows:
            if not head or not tail or head == tail:
                continue
            w.writerow([head, tail, "ant", f"{confidence:.6g}"])
    return len(rows)


def collect_mirror_pairs_for_head(
    db: Session,
    head: str,
    *,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
    include_static: bool = True,
    graph: Optional[CharRelationGraph] = None,
) -> List[Tuple[str, str]]:
    port = thesaurus or default_thesaurus_port()
    lexicon = membership if membership is not None else load_db_char_set(db)
    g = graph or get_process_cached_graph(db, port, membership=lexicon)
    seeds = direct_ant_seeds_for_head(
        db, head, thesaurus=port, membership=lexicon, include_static=include_static
    )
    return mirror_ant_pairs(
        head,
        seeds,
        syn_neighbors_of=lambda s: g.direct_syn_neighbors(s, include_static=include_static),
        membership=lexicon,
    )


__all__ = [
    "MIRROR_CONFIDENCE",
    "MIRROR_SOURCE",
    "collect_lexicon_mirror_pairs",
    "collect_mirror_pairs_for_head",
    "mirror_ant_pairs",
    "write_mirror_ant_pairs_tsv",
]
