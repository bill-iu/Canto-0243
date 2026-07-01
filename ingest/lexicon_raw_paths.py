"""Resolve lexicon SSOT raw files (primary path + maintainer-local legacy fallbacks)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]

# ponytail: legacy maintainer layout under data/raw/; both trees stay gitignored
_LEGACY_BY_ID: dict[str, tuple[str, ...]] = {
    "words_hk": ("data/raw/words.hk/wordslist.json",),
    "kaifang": ("data/raw/kaifang",),
}


def _candidate_paths(src: dict[str, Any], repo_root: Path) -> list[Path]:
    rel = src.get("raw_path")
    paths: list[Path] = []
    if rel:
        p = Path(rel)
        paths.append(p if p.is_absolute() else repo_root / p)
    for rel_legacy in _LEGACY_BY_ID.get(str(src.get("id") or ""), ()):
        leg = Path(rel_legacy)
        paths.append(leg if leg.is_absolute() else repo_root / leg)
    return paths


def resolve_lexicon_raw_path(
    src: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> Optional[Path]:
    base = repo_root or ROOT
    for path in _candidate_paths(src, base):
        if path.is_file():
            return path
        if path.is_dir():
            txts = sorted(path.glob("*.txt"))
            if txts:
                return txts[0]
    return None


__all__ = ["ROOT", "resolve_lexicon_raw_path"]
