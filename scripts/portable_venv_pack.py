#!/usr/bin/env python3
"""Portable venv pack transport (ADR-0067): zip venv/ for ship, extract-once on start."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

PACK_NAME = "venv.pack"
MARKER_NAME = ".portable-venv-extracted"
LOCK_NAME = ".portable-venv-extract.lock"
PACK_META_NAME = "portable-venv-pack.json"
SLIM_REPORT_NAME = "portable-venv-slim.json"
# After successful extract, pack is deleted (grill B).
DELETE_PACK_AFTER_OK = True


def pack_path(root: Path) -> Path:
    return root / PACK_NAME


def marker_path(root: Path) -> Path:
    return root / "venv" / MARKER_NAME


def lock_path(root: Path) -> Path:
    return root / "venv" / LOCK_NAME


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_files(root: Path) -> int:
    n = 0
    for p in root.rglob("*"):
        if p.is_file():
            n += 1
    return n


def _venv_python_ok(venv_dir: Path) -> bool:
    """Win layout (Scripts + python-home) or POSIX bin/python."""
    win_py = venv_dir / "Scripts" / "python.exe"
    if win_py.is_file():
        return (venv_dir / "python-home" / "python.exe").is_file()
    return (venv_dir / "bin" / "python").is_file()


def pack_portable_venv(root: Path) -> dict[str, int | str]:
    """Zip root/venv -> root/venv.pack, remove venv tree. Call after self-check + warm."""
    root = root.resolve()
    venv_dir = root / "venv"
    if not venv_dir.is_dir():
        raise FileNotFoundError(f"no venv to pack: {venv_dir}")
    if not _venv_python_ok(venv_dir):
        raise RuntimeError(f"venv incomplete, refuse pack: {venv_dir}")

    unpacked = count_files(venv_dir)
    # Keep slim report at bundle root for manifest (venv/ goes away).
    slim_src = venv_dir / SLIM_REPORT_NAME
    if slim_src.is_file():
        shutil.copy2(slim_src, root / SLIM_REPORT_NAME)

    out = pack_path(root)
    if out.is_file():
        out.unlink()

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(venv_dir.rglob("*")):
            if not path.is_file():
                continue
            arc = path.relative_to(venv_dir).as_posix()
            zf.write(path, arcname=arc)

    sha = file_sha256(out)
    meta = {
        "venv_pack_sha256": sha,
        "venv_unpacked_file_count": unpacked,
        "venv_pack_bytes": out.stat().st_size,
        "pack_name": PACK_NAME,
    }
    (root / PACK_META_NAME).write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    shutil.rmtree(venv_dir)
    print(
        f"Portable venv pack (C11-2): {unpacked} files -> {PACK_NAME} "
        f"({out.stat().st_size} bytes, sha256={sha[:12]}…)"
    )
    return meta


def _read_marker(root: Path) -> dict | None:
    mp = marker_path(root)
    if not mp.is_file():
        return None
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_marker(root: Path, pack_sha: str) -> None:
    venv_dir = root / "venv"
    venv_dir.mkdir(parents=True, exist_ok=True)
    payload = {"pack_sha256": pack_sha, "extracted_at": int(time.time())}
    marker_path(root).write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _acquire_lock(root: Path, *, timeout_s: float = 600.0) -> Path:
    """Create exclusive lock file under venv/. Stale locks older than timeout are stolen."""
    venv_dir = root / "venv"
    venv_dir.mkdir(parents=True, exist_ok=True)
    lp = lock_path(root)
    deadline = time.time() + timeout_s
    while True:
        try:
            fd = os.open(str(lp), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("ascii"))
            finally:
                os.close(fd)
            return lp
        except FileExistsError:
            try:
                age = time.time() - lp.stat().st_mtime
            except OSError:
                age = 0
            if age > timeout_s:
                try:
                    lp.unlink()
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                raise TimeoutError(f"venv extract lock busy: {lp}")
            time.sleep(0.5)


def _release_lock(lp: Path) -> None:
    try:
        lp.unlink()
    except OSError:
        pass


def _progress(done: int, total: int) -> None:
    if total <= 0:
        return
    pct = min(100, int(100 * done / total))
    if done == total or done == 1 or done % max(1, total // 20) == 0:
        print(f"  extract {done}/{total} ({pct}%)", file=sys.stderr, flush=True)


def extract_once(root: Path, *, progress: bool = True) -> str:
    """Ensure venv/ is ready. Returns status: ready|extracted|noop."""
    root = root.resolve()
    pack = pack_path(root)
    venv_dir = root / "venv"
    marker = _read_marker(root)

    if not pack.is_file():
        if _venv_python_ok(venv_dir):
            return "ready"
        if marker is not None:
            raise RuntimeError(
                "venv marker present but runtime missing and no venv.pack; re-download package"
            )
        raise FileNotFoundError(f"no venv and no {PACK_NAME} under {root}")

    pack_sha = file_sha256(pack)
    if marker and marker.get("pack_sha256") == pack_sha and _venv_python_ok(venv_dir):
        # Extract ok but pack delete failed previously
        if DELETE_PACK_AFTER_OK:
            try:
                pack.unlink()
            except OSError:
                pass
        return "ready"

    print("首次解壓 runtime（venv.pack），請稍候…", flush=True)
    lp = _acquire_lock(root)
    try:
        # Re-check under lock
        if not pack.is_file():
            if _venv_python_ok(venv_dir):
                return "ready"
            raise FileNotFoundError(f"{PACK_NAME} disappeared under lock")

        pack_sha = file_sha256(pack)
        if venv_dir.is_dir():
            # Wipe partial tree; keep pack at root
            for child in list(venv_dir.iterdir()):
                if child.name == LOCK_NAME:
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()

        with zipfile.ZipFile(pack, "r") as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            total = len(names)
            for i, name in enumerate(names, 1):
                zf.extract(name, path=venv_dir)
                if progress:
                    _progress(i, total)

        if not _venv_python_ok(venv_dir):
            raise RuntimeError("extract finished but venv python missing")

        _write_marker(root, pack_sha)
        if DELETE_PACK_AFTER_OK:
            pack.unlink()
        print("runtime 解壓完成。", flush=True)
        return "extracted"
    except Exception:
        # Leave pack; drop broken venv (except lock, released below)
        if venv_dir.is_dir():
            for child in list(venv_dir.iterdir()):
                if child.name == LOCK_NAME:
                    continue
                try:
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                except OSError:
                    pass
        raise
    finally:
        _release_lock(lp)


def ensure_portable_venv(root: Path) -> str:
    """Public entry for launchers: extract if needed, idempotent."""
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            return extract_once(root)
        except Exception as e:
            last_err = e
            if attempt == 0:
                print(f"extract retry after: {e}", file=sys.stderr, flush=True)
                continue
            break
    assert last_err is not None
    raise last_err


def main() -> int:
    p = argparse.ArgumentParser(description="Portable venv.pack (ADR-0067)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pack_p = sub.add_parser("pack", help="Zip venv/ -> venv.pack and remove tree")
    pack_p.add_argument("root", type=Path)

    ens = sub.add_parser("ensure", help="Extract-once if venv.pack present")
    ens.add_argument("root", type=Path)

    args = p.parse_args()
    root = args.root.resolve()
    if args.cmd == "pack":
        pack_portable_venv(root)
        return 0
    status = ensure_portable_venv(root)
    print(f"OK ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
