"""Per-source lexicon candidate layer cache (C3).

Caches immutable parse output keyed by source id + parser + input hashes.
Merge/overlay always re-run; DB write remains full wipe+persist.
"""
from __future__ import annotations

import hashlib
import os
import pickle
import re
from pathlib import Path
from typing import Any, Optional

from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_raw_paths import ROOT, resolve_lexicon_raw_path
from ingest.lexicon_sources import ingest_source
from ingest.syn_ant_manifest import resolve_source_path

# Bump when candidate pickle layout or parser output semantics change.
LAYER_CACHE_FORMAT = "1"
DEFAULT_CACHE_DIR = ROOT / ".cache" / "lexicon-layers"
_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def layer_cache_enabled(*, explicit: Optional[bool] = None) -> bool:
    if explicit is not None:
        return explicit
    flag = os.environ.get("LEXICON_LAYER_CACHE", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def _safe_id(value: str) -> str:
    return _SAFE.sub("_", value)[:80] or "src"


def _file_digest(path: Path, h: Any) -> None:
    h.update(str(path).encode("utf-8", "replace"))
    h.update(b"\0")
    if not path.exists():
        h.update(b"MISSING")
        return
    if path.is_file():
        h.update(path.read_bytes())
        return
    # Directory: content-address children (sorted); ponytail ceiling = large trees
    for child in sorted(path.rglob("*")):
        if child.is_file():
            h.update(str(child.relative_to(path)).encode("utf-8", "replace"))
            h.update(b"\0")
            h.update(child.read_bytes())
            h.update(b"\0")


def source_input_paths(src: dict[str, Any], *, repo_root: Path | None = None) -> list[Path]:
    root = repo_root or ROOT
    paths: list[Path] = []
    raw = resolve_lexicon_raw_path(src, repo_root=root) or resolve_source_path(src)
    if raw is not None:
        paths.append(Path(raw))
    for key in ("allowlist_path", "reject_suffixes_path", "reject_literals_path"):
        raw_rel = src.get(key) or ""
        if not raw_rel:
            continue
        p = Path(str(raw_rel))
        if not p.is_absolute():
            p = root / p
        paths.append(p)
    return paths


def fingerprint_source(src: dict[str, Any], *, repo_root: Path | None = None) -> str:
    h = hashlib.sha256()
    h.update(LAYER_CACHE_FORMAT.encode())
    h.update(b"\0")
    h.update(str(src.get("id") or "").encode())
    h.update(b"\0")
    h.update(str(src.get("parser") or "").encode())
    h.update(b"\0")
    h.update(str(src.get("source_rank") or "").encode())
    h.update(b"\0")
    for path in source_input_paths(src, repo_root=repo_root):
        _file_digest(path, h)
        h.update(b"\0")
    return h.hexdigest()[:32]


def cache_path_for(
    src: dict[str, Any],
    fp: str,
    *,
    cache_dir: Path | None = None,
) -> Path:
    base = cache_dir or DEFAULT_CACHE_DIR
    name = f"{_safe_id(str(src.get('id') or 'src'))}__{_safe_id(str(src.get('parser') or 'p'))}__{fp}.pkl"
    return base / name


def _dump_candidates(path: Path, batch: list[LexiconCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [(c.char, c.jyutping, c.code, c.sources) for c in batch]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(pickle.dumps(payload, protocol=4))
    tmp.replace(path)


def _load_candidates(path: Path) -> list[LexiconCandidate]:
    payload = pickle.loads(path.read_bytes())
    out: list[LexiconCandidate] = []
    for char, jyutping, code, sources in payload:
        out.append(
            LexiconCandidate(
                char=str(char),
                jyutping=str(jyutping),
                code=str(code),
                sources=tuple(sources),
            )
        )
    return out


def _purge_stale(src: dict[str, Any], keep: Path, *, cache_dir: Path) -> None:
    prefix = f"{_safe_id(str(src.get('id') or 'src'))}__{_safe_id(str(src.get('parser') or 'p'))}__"
    for old in cache_dir.glob(prefix + "*.pkl"):
        if old.resolve() != keep.resolve():
            try:
                old.unlink()
            except OSError:
                pass


def load_or_ingest_source(
    src: dict[str, Any],
    *,
    use_cache: bool = True,
    cache_dir: Path | None = None,
    repo_root: Path | None = None,
) -> tuple[list[LexiconCandidate], str]:
    """Return (candidates, 'hit'|'miss'|'off')."""
    if not use_cache:
        return ingest_source(src), "off"

    base = cache_dir or DEFAULT_CACHE_DIR
    fp = fingerprint_source(src, repo_root=repo_root)
    path = cache_path_for(src, fp, cache_dir=base)
    if path.is_file():
        try:
            return _load_candidates(path), "hit"
        except Exception:
            pass

    batch = ingest_source(src)
    try:
        _dump_candidates(path, batch)
        _purge_stale(src, path, cache_dir=base)
    except OSError:
        pass
    return batch, "miss"
