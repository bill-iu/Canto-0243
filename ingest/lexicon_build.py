"""Collect, overlay, and persist lexicon candidates."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import DEFAULT_TSV, load_corrections
from app.models.word import Word, WordSource
from app.utils.jyutping_codec import split_jyutping
from ingest.lexicon_merge import merge_lexicon_candidates
from ingest.lexicon_overlay import apply_lexicon_overlay
from ingest.lexicon_sources import ingest_source
from ingest.lexicon_stats import lexicon_source_availability
from ingest.syn_ant_manifest import load_manifest, select_sources

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON_MANIFEST = ROOT / "data" / "lexicon" / "sources.yaml"
PERSIST_CHUNK = 2000


def collect_lexicon_candidates(
    manifest_path: Path | str | None = None,
    *,
    source_ids: Optional[List[str]] = None,
    repo_root: Path | None = None,
) -> list[LexiconCandidate]:
    manifest = load_manifest(manifest_path or DEFAULT_LEXICON_MANIFEST)
    sources = select_sources(
        manifest,
        source_ids=source_ids,
        defaults_only=not bool(source_ids),
    )
    missing_required: list[str] = []
    layers: list[tuple[int, list[LexiconCandidate]]] = []
    for src in sources:
        if not lexicon_source_availability(src, repo_root=repo_root).get("available"):
            if src.get("local_only"):
                continue  # ponytail: maintainer-local; skip when raw absent
            missing_required.append(str(src["id"]))
            continue
        batch = ingest_source(src)
        layers.append((int(src.get("source_rank") or 50), batch))
    if missing_required:
        raise FileNotFoundError(
            f"enabled lexicon sources missing raw files: {', '.join(missing_required)}"
        )
    merged = merge_lexicon_candidates(layers)
    corrections = load_corrections(DEFAULT_TSV)
    return apply_lexicon_overlay(merged, corrections)


def persist_lexicon_candidates(db: Session, candidates: list[LexiconCandidate]) -> int:
    count = 0
    for off in range(0, len(candidates), PERSIST_CHUNK):
        chunk = candidates[off : off + PERSIST_CHUNK]
        words: list[Word] = []
        for c in chunk:
            initials, finals, tones = split_jyutping(c.jyutping)
            words.append(
                Word(
                    char=c.char,
                    jyutping=c.jyutping,
                    code=c.code,
                    initials=initials,
                    finals=finals,
                    tones=tones,
                    length=len(c.char),
                )
            )
        db.add_all(words)
        db.flush()
        for word, cand in zip(words, chunk):
            for src in cand.sources:
                db.add(WordSource(word_id=word.id, source=src[:32]))
        count += len(chunk)
    return count


def build_lexicon_words(
    db: Session,
    *,
    manifest_path: Path | str | None = None,
    source_ids: Optional[List[str]] = None,
) -> int:
    candidates = collect_lexicon_candidates(manifest_path, source_ids=source_ids)
    return persist_lexicon_candidates(db, candidates)
