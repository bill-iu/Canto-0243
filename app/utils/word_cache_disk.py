"""詞庫快取磁碟 adapter — 暖啟快照讀寫（實作細節，非索引介面）。"""
from __future__ import annotations

import os
import pickle
from pathlib import Path

from app.utils import word_cache_index as index

_DISK_CACHE_VERSION = 1


def disk_cache_enabled() -> bool:
    return os.getenv("WORD_CACHE_DISK", "1").lower() not in ("0", "false", "no")


def disk_cache_path() -> Path:
    from app.db.connection import PROJECT_ROOT

    return PROJECT_ROOT / ".cache" / "word_meta.bin"


def _sqlite_fingerprint() -> dict | None:
    from app.db.connection import DATABASE_URL, PROJECT_ROOT

    if not DATABASE_URL.startswith("sqlite"):
        return None
    raw = DATABASE_URL.removeprefix("sqlite:///")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.is_file():
        return None
    st = path.stat()
    return {
        "version": _DISK_CACHE_VERSION,
        "mtime_ns": st.st_mtime_ns,
        "size": st.st_size,
        "path": str(path.resolve()),
    }


def try_restore(*, on_progress=None) -> bool:
    fp = _sqlite_fingerprint()
    if not fp:
        return False
    cache_path = disk_cache_path()
    if not cache_path.is_file():
        return False
    try:
        with cache_path.open("rb") as handle:
            payload = pickle.load(handle)
        if payload.get("fingerprint") != fp:
            return False
        index.install_state(payload["state"])
        if on_progress is not None:
            on_progress(0.99)
        return index.is_populated()
    except Exception:
        return False


def persist() -> None:
    fp = _sqlite_fingerprint()
    if not fp or not index.is_populated():
        return
    cache_path = disk_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprint": fp, "state": index.export_state()}
    tmp_path = cache_path.with_suffix(".tmp")
    with tmp_path.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(cache_path)
