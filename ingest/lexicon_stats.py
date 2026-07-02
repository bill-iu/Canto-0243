"""Lexicon build coverage stats (maintainer release gate)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.word import Word
from ingest.lexicon_raw_paths import ROOT, resolve_lexicon_raw_path

_LEXICON_RAW_PARSERS = frozenset({"words_hk_wordslist", "kaifang_txt", "lexicon_json"})


def lexicon_source_availability(
    src: dict,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Like syn_ant source_availability but honors data/raw fallbacks."""
    base = repo_root or ROOT
    info: dict[str, object] = {"id": src.get("id"), "available": True, "missing": []}
    parser = str(src.get("parser") or "")
    if parser == "rime_char":
        rel = src.get("raw_path")
        raw = (base / rel) if rel else None
    elif parser in _LEXICON_RAW_PARSERS:
        raw = resolve_lexicon_raw_path(src, repo_root=base)
    else:
        from ingest.syn_ant_manifest import resolve_source_path

        raw = resolve_source_path(src)
    if raw is None or not raw.exists():
        info["available"] = False
        missing = info["missing"]
        assert isinstance(missing, list)
        missing.append(str(src.get("raw_path") or raw))
    return info


def lexicon_word_stats(db: Session) -> dict[str, int]:
    total = db.query(Word).count()
    multi = db.query(Word).filter(Word.length >= 2).count()
    return {"total": total, "multi_char": multi}


def check_min_multi_char(db: Session, minimum: int) -> None:
    stats = lexicon_word_stats(db)
    got = int(stats["multi_char"])
    if got < minimum:
        raise ValueError(
            f"lexicon multi-char words {got} < required {minimum} "
            f"(total={stats['total']}); check data/raw or data/lexicon/raw"
        )


__all__ = [
    "check_min_multi_char",
    "lexicon_source_availability",
    "lexicon_word_stats",
]
