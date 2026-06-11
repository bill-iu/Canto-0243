"""Ingest 0243-style 2-char antonym compounds into single-char ant word_relations."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word, WordRelation
from ingest.relation_canonical import canonical_word_ids
from ingest.syn_ant_merge import (
    _fetch_existing_keys,
    _insert_relations,
    clear_word_relations_source,
    get_char_to_primary_id,
)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "syn_ant" / "compound_antonyms.txt"


def load_compound_antonyms(path: Path | None = None) -> List[str]:
    """Load deduplicated 2-char compound list (order preserved)."""
    p = path or DEFAULT_PATH
    seen: Set[str] = set()
    out: List[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for token in line.replace("，", " ").replace(",", " ").split():
            ch = token.strip()
            if len(ch) != 2 or ch in seen:
                continue
            seen.add(ch)
            out.append(ch)
    return out


def _compound_exists(db: Session, compound: str) -> bool:
    return (
        db.query(Word.id)
        .filter(Word.char == compound, Word.length == 2)
        .first()
        is not None
    )


def ingest_compound_ant_char_pairs(
    db: Session,
    compounds: Iterable[str],
    *,
    source: str = "compound_ant",
    confidence: float = 0.9,
    dedupe_existing: bool = True,
    replace_source: bool = False,
) -> dict:
    """For each compound in DB, insert single-char ant relation between its two chars."""
    source = (source or "compound_ant")[:32]
    stats = {
        "input_compounds": 0,
        "unique_compounds": 0,
        "matched_in_db": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_no_compound": 0,
        "skipped_no_char_id": 0,
        "skipped_existing": 0,
        "matched_chars": [],
    }

    unique: List[str] = []
    seen: Set[str] = set()
    for c in compounds:
        stats["input_compounds"] += 1
        if len(c) != 2 or c in seen:
            continue
        seen.add(c)
        unique.append(c)
    stats["unique_compounds"] = len(unique)

    if replace_source:
        stats["cleared"] = clear_word_relations_source(db, source)

    char_to_id = get_char_to_primary_id(db)
    pair_keys: Dict[Tuple[int, int, str], dict] = {}

    for compound in unique:
        if not _compound_exists(db, compound):
            stats["skipped_no_compound"] += 1
            continue
        stats["matched_in_db"] += 1
        stats["matched_chars"].append(compound)

        a, b = compound[0], compound[1]
        id_a = char_to_id.get(a)
        id_b = char_to_id.get(b)
        if not id_a or not id_b:
            stats["skipped_no_char_id"] += 1
            continue
        w, r = canonical_word_ids(id_a, id_b)
        if w == r:
            continue
        key = (w, r, "ant")
        if key not in pair_keys:
            pair_keys[key] = {
                "word_id": w,
                "related_id": r,
                "relation_type": "ant",
                "score": confidence,
                "source": source,
            }

    stats["candidate_pairs"] = len(pair_keys)
    pending = list(pair_keys.values())
    if not pending:
        return stats

    if dedupe_existing:
        keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in pending]
        existing = _fetch_existing_keys(db, keys)
        before = len(pending)
        pending = [
            c for c in pending
            if (c["word_id"], c["related_id"], c["relation_type"]) not in existing
        ]
        stats["skipped_existing"] = before - len(pending)

    if pending:
        stats["inserted"] = _insert_relations(db, [WordRelation(**c) for c in pending])

    return stats
