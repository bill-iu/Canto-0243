"""Payload root: Desktop sidecar dir (lyrics.db + data + client) or repo checkout.

When the app is installed via wheel (PyApp), code lives under site-packages;
sidecar data stays next to the launcher. Prefer CANTO_PAYLOAD_ROOT (set by
desktop_entry / local_launch), then cwd, then dev-repo layout.
"""
from __future__ import annotations

import os
from pathlib import Path


def resolve_payload_root() -> Path:
    env = (os.environ.get("CANTO_PAYLOAD_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    cwd = Path.cwd().resolve()
    if (cwd / "lyrics.db").is_file():
        return cwd

    # Dev: this file is <repo>/app/payload_root.py
    repo = Path(__file__).resolve().parents[1]
    if (repo / "main.py").is_file() and (repo / "app").is_dir():
        return repo

    return cwd
