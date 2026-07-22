"""Payload root SSOT (ADR-0068): Desktop sidecar or repo checkout.

Prefer CANTO_PAYLOAD_ROOT (set by desktop-shell / desktop_entry / local_launch
before importing app.db). Code in wheels lives under site-packages; lyrics.db +
UI + data stay next to the package root.

Resolution order:
  1. CANTO_PAYLOAD_ROOT env
  2. cwd if it contains lyrics.db
  3. PyApp / frozen sidecar guess (exe dir or parent of runtime/)
  4. Dev repo layout (main.py + app/)
  5. cwd
"""
from __future__ import annotations

import functools
import os
import sys
from pathlib import Path


def _env_root() -> Path | None:
    env = (os.environ.get("CANTO_PAYLOAD_ROOT") or "").strip()
    if not env:
        return None
    return Path(env).expanduser().resolve()


def _cwd_with_db() -> Path | None:
    cwd = Path.cwd().resolve()
    if (cwd / "lyrics.db").is_file():
        return cwd
    return None


def _pyapp_sidecar_guess() -> Path | None:
    """When shell did not set env: prefer package root that holds lyrics.db.

    Inner PyApp binary may live under package/runtime/; outer shell next to
    lyrics.db. Do not treat bare sys.executable.parent as payload unless it
    has lyrics.db (avoids %LOCALAPPDATA%/pyapp/... false roots).
    """
    if os.environ.get("PYAPP") != "1" and not getattr(sys, "frozen", False):
        return None
    try:
        exe = Path(sys.executable).resolve()
    except (OSError, RuntimeError):
        return None
    cand = exe.parent
    if (cand / "lyrics.db").is_file():
        return cand
    # runtime/Canto-0243-runtime.exe → package root
    if cand.name.lower() == "runtime":
        outer = cand.parent
        if (outer / "lyrics.db").is_file():
            return outer
    return None


def _dev_repo_root() -> Path | None:
    # This file is <repo>/app/payload_root.py
    repo = Path(__file__).resolve().parents[1]
    if (repo / "main.py").is_file() and (repo / "app").is_dir():
        return repo
    return None


def resolve_payload_root() -> Path:
    """Resolve payload root without caching (tests may change env)."""
    for candidate in (
        _env_root(),
        _cwd_with_db(),
        _pyapp_sidecar_guess(),
        _dev_repo_root(),
    ):
        if candidate is not None:
            return candidate
    return Path.cwd().resolve()


@functools.lru_cache(maxsize=1)
def get_payload_root() -> Path:
    """Cached root for runtime; clear via clear_payload_root_cache after env bind."""
    return resolve_payload_root()


def clear_payload_root_cache() -> None:
    get_payload_root.cache_clear()


def bind_payload_root(root: Path | str | None = None) -> Path:
    """Set CANTO_PAYLOAD_ROOT and refresh cache. Call before importing app.db."""
    path = Path(root).expanduser().resolve() if root is not None else resolve_payload_root()
    os.environ["CANTO_PAYLOAD_ROOT"] = str(path)
    clear_payload_root_cache()
    # Warm cache with bound value
    get_payload_root()
    return path
