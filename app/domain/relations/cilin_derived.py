"""詞林衍生反義 — per-head 字面對核心（CONTEXT § 詞林衍生反義）。"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.ranking import DERIVED_ANT_SOURCES
from app.domain.relations.valid_term import normalize_literal
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port
from app.models.word import Word
from app.repositories.word_relation_repo import (
    fetch_bidirectional_relations,
    load_db_char_set,
)

CILIN_DERIVED_SOURCE = "ant_cilin_exanded"
CILIN_DERIVED_CONFIDENCE = 0.75

_HANZI = re.compile(r"[\u4e00-\u9fff]")


def cilin_derived_ant_pairs(
    head: str,
    ant_seeds: Iterable[str],
    *,
    cilin_synonyms_of: Callable[[str], Iterable[str]],
    membership: Set[str],
) -> List[Tuple[str, str]]:
    """Per-head 詞林衍生反義：(head, cilin_syn(ant_seed))，收錄閘 + 去重。"""
    h = (head or "").strip()
    if not h:
        return []
    out: List[Tuple[str, str]] = []
    seen_tails: Set[str] = {h}
    for seed in ant_seeds:
        seed = (seed or "").strip()
        if not seed:
            continue
        for syn in cilin_synonyms_of(seed):
            tail = normalize_literal(syn)
            if not tail or tail == h or tail in seen_tails or tail not in membership:
                continue
            seen_tails.add(tail)
            out.append((h, tail))
    return out


def direct_ant_seeds_for_head(
    db: Session,
    head: str,
    *,
    thesaurus: ThesaurusPort,
    membership: Set[str],
    include_static: bool = True,
) -> List[str]:
    """直接反義種子：DB ant（排除衍生 source）＋ 靜態詞林埠反義。"""
    q = (head or "").strip()
    if not q:
        return []
    seeds: List[str] = []
    seen: Set[str] = {q}
    word_ids = [w.id for w in db.query(Word.id).filter(Word.char == q).all()]
    for rtype, rchar, source, *_rest in fetch_bidirectional_relations(db, word_ids):
        if rtype != "ant" or not rchar:
            continue
        if (source or "") in DERIVED_ANT_SOURCES:
            continue
        ch = normalize_literal(rchar)
        if not ch or ch == q or ch not in membership or ch in seen:
            continue
        seen.add(ch)
        seeds.append(ch)
    if include_static:
        thesaurus.ensure_loaded()
        for ant in thesaurus.get_antonyms(q):
            ch = normalize_literal(ant)
            if not ch or ch == q or ch not in membership or ch in seen:
                continue
            seen.add(ch)
            seeds.append(ch)
    return seeds


def collect_lexicon_cilin_derived_pairs(
    db: Session,
    thesaurus: ThesaurusPort,
    membership: Optional[Set[str]] = None,
    *,
    include_static: bool = True,
) -> List[Tuple[str, str]]:
    """Bake adapter：逐收錄 head 呼叫同一 per-head 核心。"""
    lexicon = membership if membership is not None else load_db_char_set(db)
    if not lexicon:
        return []

    def cilin_fn(word: str) -> List[str]:
        thesaurus.ensure_loaded()
        return thesaurus.get_cilin_synonyms(word)

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
        for pair in cilin_derived_ant_pairs(
            head,
            seeds,
            cilin_synonyms_of=cilin_fn,
            membership=lexicon,
        ):
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def write_cilin_derived_pairs_tsv(
    path: Path | str,
    pairs: Iterable[Tuple[str, str]],
    *,
    confidence: float = CILIN_DERIVED_CONFIDENCE,
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


def collect_cilin_derived_for_head(
    db: Session,
    head: str,
    *,
    thesaurus: Optional[ThesaurusPort] = None,
    membership: Optional[Set[str]] = None,
    include_static: bool = True,
) -> List[Tuple[str, str]]:
    """Runtime/bake 共用：單一 head 的詞林衍生反義字面對。"""
    port = thesaurus or default_thesaurus_port()
    lexicon = membership if membership is not None else load_db_char_set(db)
    seeds = direct_ant_seeds_for_head(
        db, head, thesaurus=port, membership=lexicon, include_static=include_static
    )

    def cilin_fn(word: str) -> List[str]:
        port.ensure_loaded()
        return port.get_cilin_synonyms(word)

    return cilin_derived_ant_pairs(
        head,
        seeds,
        cilin_synonyms_of=cilin_fn,
        membership=lexicon,
    )


__all__ = [
    "CILIN_DERIVED_CONFIDENCE",
    "CILIN_DERIVED_SOURCE",
    "cilin_derived_ant_pairs",
    "collect_cilin_derived_for_head",
    "collect_lexicon_cilin_derived_pairs",
    "direct_ant_seeds_for_head",
    "write_cilin_derived_pairs_tsv",
]
