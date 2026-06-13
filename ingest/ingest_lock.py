"""Cross-process ingest singleton lock (PID-based stale detection)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK_DIR = REPO_ROOT / "data" / "locks"


class IngestLockError(RuntimeError):
    """Another ingest process holds the lock."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, SystemError):
        return False
    return True


def _read_lock_pid(path: Path) -> Optional[int]:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    try:
        return int(text.splitlines()[0].strip())
    except ValueError:
        return None


def acquire_ingest_lock(name: str, *, lock_dir: Path | None = None) -> Path:
    """Acquire exclusive ingest lock; raise IngestLockError if another live PID holds it."""
    directory = lock_dir or DEFAULT_LOCK_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.lock"
    pid = os.getpid()

    if path.exists():
        holder = _read_lock_pid(path)
        if holder == pid:
            return path
        if holder is not None and _pid_alive(holder):
            raise IngestLockError(
                f"Ingest '{name}' already running (PID {holder}). Lock: {path}"
            )
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise IngestLockError(f"Cannot replace stale lock at {path}: {exc}") from exc

    path.write_text(f"{pid}\n", encoding="utf-8")
    return path


def release_ingest_lock(path: Path) -> None:
    try:
        holder = _read_lock_pid(path)
        if holder is None or holder == os.getpid():
            path.unlink(missing_ok=True)
    except OSError:
        pass


@contextmanager
def ingest_lock(name: str, *, lock_dir: Path | None = None) -> Iterator[Path]:
    path = acquire_ingest_lock(name, lock_dir=lock_dir)
    try:
        yield path
    finally:
        release_ingest_lock(path)
