"""Collect, overlay, and persist lexicon candidates."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import DEFAULT_TSV, load_corrections
from app.utils.jyutping_codec import split_jyutping
from ingest.lexicon_merge import merge_lexicon_candidates
from ingest.lexicon_overlay import apply_lexicon_overlay
from ingest.lexicon_stats import lexicon_source_availability
from ingest.syn_ant_manifest import load_manifest, select_sources

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON_MANIFEST = ROOT / "data" / "lexicon" / "sources.yaml"
PERSIST_CHUNK = 2000

# ADR-0027: source_flags bitmask — replaces word_sources table
SOURCE_FLAG_MAP: dict[str, int] = {
    "hsk30": 1,
    "kaifang": 2,
    "rime": 4,
    "rime_phrase": 8,
    "rime_words": 16,
    "words_hk": 32,
}

_INSERT_WORDS = text(
    "INSERT INTO words (char, jyutping, code, initials, finals, source_flags, length) "
    "VALUES (:char, :jyutping, :code, :initials, :finals, :source_flags, :length)"
)


def collect_lexicon_candidates(
    manifest_path: Path | str | None = None,
    *,
    source_ids: Optional[List[str]] = None,
    repo_root: Path | None = None,
    use_layer_cache: bool | None = None,
) -> list[LexiconCandidate]:
    from ingest.lexicon_layer_cache import layer_cache_enabled, load_or_ingest_source

    manifest = load_manifest(manifest_path or DEFAULT_LEXICON_MANIFEST)
    sources = select_sources(
        manifest,
        source_ids=source_ids,
        defaults_only=not bool(source_ids),
    )
    use_cache = layer_cache_enabled(explicit=use_layer_cache)
    missing_required: list[str] = []
    layers: list[tuple[int, list[LexiconCandidate]]] = []
    hits = misses = offs = 0
    for src in sources:
        if not lexicon_source_availability(src, repo_root=repo_root).get("available"):
            if src.get("local_only"):
                continue  # ponytail: maintainer-local; skip when raw absent
            missing_required.append(str(src["id"]))
            continue
        batch, status = load_or_ingest_source(
            src, use_cache=use_cache, repo_root=repo_root
        )
        if status == "hit":
            hits += 1
        elif status == "miss":
            misses += 1
        else:
            offs += 1
        layers.append((int(src.get("source_rank") or 50), batch))
    if missing_required:
        raise FileNotFoundError(
            f"enabled lexicon sources missing raw files: {', '.join(missing_required)}"
        )
    if use_cache:
        print(f"    layer-cache: hit={hits} miss={misses}")
    else:
        print(f"    layer-cache: off ({offs} source(s) parsed)")
    merged = merge_lexicon_candidates(layers)
    corrections = load_corrections(DEFAULT_TSV)
    return apply_lexicon_overlay(merged, corrections)


def _candidate_row(c: LexiconCandidate) -> dict:
    initials, finals, _ = split_jyutping(c.jyutping)
    flags = 0
    for src in c.sources:
        flags |= SOURCE_FLAG_MAP.get(src, 0)
    return {
        "char": c.char,
        "jyutping": c.jyutping,
        "code": c.code,
        "initials": initials,
        "finals": finals,
        "source_flags": flags,
        "length": len(c.char),
    }


def persist_lexicon_candidates(db: Session, candidates: list[LexiconCandidate]) -> int:
    """Bulk INSERT words (no ORM instances) — same chunk style as relation bulk_insert."""
    if not candidates:
        return 0
    for off in range(0, len(candidates), PERSIST_CHUNK):
        chunk = candidates[off : off + PERSIST_CHUNK]
        db.execute(_INSERT_WORDS, [_candidate_row(c) for c in chunk])
    db.expire_all()
    return len(candidates)


def assert_persisted_matches_candidates(
    db: Session,
    candidates: list[LexiconCandidate],
    *,
    sample_n: int = 5,
) -> None:
    """Fail if DB words diverge from overlay candidates (count + head/tail samples)."""
    n = db.execute(text("SELECT COUNT(*) FROM words")).scalar()
    if int(n or 0) != len(candidates):
        raise AssertionError(
            f"words count {n} != candidates {len(candidates)}"
        )
    if not candidates:
        return
    idxs = sorted({0, len(candidates) - 1, *range(0, len(candidates), max(1, len(candidates) // sample_n))})[
        : sample_n + 2
    ]
    for i in idxs:
        c = candidates[i]
        row = db.execute(
            text(
                "SELECT char, jyutping, code FROM words "
                "WHERE char = :char AND jyutping = :jyutping"
            ),
            {"char": c.char, "jyutping": c.jyutping},
        ).first()
        if row is None:
            raise AssertionError(f"missing row for {c.char!r} / {c.jyutping!r}")
        if row[2] != c.code:
            raise AssertionError(
                f"code mismatch for {c.char!r}: db={row[2]!r} cand={c.code!r}"
            )


def build_lexicon_words(
    db: Session,
    *,
    manifest_path: Path | str | None = None,
    source_ids: Optional[List[str]] = None,
    use_layer_cache: bool | None = None,
) -> int:
    candidates = collect_lexicon_candidates(
        manifest_path,
        source_ids=source_ids,
        use_layer_cache=use_layer_cache,
    )
    return persist_lexicon_candidates(db, candidates)
