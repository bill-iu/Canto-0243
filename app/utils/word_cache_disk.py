"""詞庫快取磁碟 adapter — 暖啟快照讀寫（實作細節，非索引介面）。"""
from __future__ import annotations

import hashlib
import os
import pickle
from pathlib import Path

from app.utils import word_cache_index as index

_DISK_CACHE_VERSION = 2
_CHUNK = 1 << 20


def disk_cache_enabled() -> bool:
    return os.getenv("WORD_CACHE_DISK", "1").lower() not in ("0", "false", "no")


def _project_root() -> Path:
    from app.db.connection import PROJECT_ROOT

    return PROJECT_ROOT


def disk_cache_path(*, cache_dir: Path | None = None) -> Path:
    base = cache_dir if cache_dir is not None else _project_root() / ".cache"
    return base / "word_meta.bin"


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_sqlite_db_path(db_path: Path | None = None) -> Path | None:
    if db_path is not None:
        return db_path.resolve()
    from app.db.connection import DATABASE_URL, PROJECT_ROOT

    if not DATABASE_URL.startswith("sqlite"):
        return None
    raw = DATABASE_URL.removeprefix("sqlite:///")
    path = Path(raw)
    if not path.is_absolute():
        path = (PROJECT_ROOT / raw.removeprefix("./")).resolve()
    return path if path.is_file() else None


def fingerprint_for_db(db_path: Path) -> dict | None:
    """內容指紋（size + digest），唔綁路徑。"""
    if not db_path.is_file():
        return None
    stat = db_path.stat()
    return {
        "version": _DISK_CACHE_VERSION,
        "size": stat.st_size,
        "digest": _digest_file(db_path),
    }


def _cache_dir_for(db_path: Path | None, cache_dir: Path | None) -> Path:
    if cache_dir is not None:
        return cache_dir
    if db_path is not None:
        return Path(db_path).resolve().parent / ".cache"
    return _project_root() / ".cache"


def try_restore(
    *,
    db_path: Path | None = None,
    cache_dir: Path | None = None,
    on_progress=None,
) -> bool:
    resolved = resolve_sqlite_db_path(db_path)
    if not resolved:
        return False
    fp = fingerprint_for_db(resolved)
    if not fp:
        return False
    cache_path = disk_cache_path(cache_dir=_cache_dir_for(db_path, cache_dir))
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


def persist(*, db_path: Path | None = None, cache_dir: Path | None = None) -> None:
    resolved = resolve_sqlite_db_path(db_path)
    if not resolved or not index.is_populated():
        return
    fp = fingerprint_for_db(resolved)
    if not fp:
        return
    target_dir = _cache_dir_for(db_path, cache_dir)
    cache_path = disk_cache_path(cache_dir=target_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprint": fp, "state": index.export_state()}
    tmp_path = cache_path.with_suffix(".tmp")
    with tmp_path.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(cache_path)
