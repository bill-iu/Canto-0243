"""C11-A: denylist slim of portable venv (reduce extract/delete file count)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

# Directory basenames removed wherever they appear under venv.
_DIR_BASENAME_DENY = frozenset(
    {
        "__pycache__",
        "idlelib",
        "turtledemo",
        "ensurepip",  # pip already installed into the bundle
    }
)

_SITE_TEST_NAMES = frozenset({"tests", "test", "testing"})


def count_files(root: Path) -> int:
    if not root.is_dir():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def _should_remove_dir(path: Path) -> bool:
    name = path.name
    if name in _DIR_BASENAME_DENY:
        return True
    # stdlib test suite: .../Lib/test or .../lib/python3.x/test
    if name == "test":
        parent = path.parent.name
        if parent in ("Lib", "lib") or parent.startswith("python"):
            return True
    if "site-packages" in path.parts and name in _SITE_TEST_NAMES:
        return True
    return False


def _iter_removable_dirs(venv_root: Path) -> list[Path]:
    found = [p for p in venv_root.rglob("*") if p.is_dir() and _should_remove_dir(p)]
    found.sort(key=lambda p: len(p.parts), reverse=True)
    return found


def slim_portable_venv(venv_dir: Path) -> dict[str, int]:
    """Remove denylisted trees and *.pyc; return before/after counts."""
    venv_dir = venv_dir.resolve()
    if not venv_dir.is_dir():
        raise FileNotFoundError(venv_dir)

    before = count_files(venv_dir)
    removed_dirs = 0
    for path in _iter_removable_dirs(venv_dir):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            removed_dirs += 1

    removed_pyc = 0
    for path in list(venv_dir.rglob("*.pyc")) + list(venv_dir.rglob("*.pyo")):
        try:
            path.unlink()
            removed_pyc += 1
        except OSError:
            pass

    stats = {
        "venv_files_before": before,
        "dirs_removed": removed_dirs,
        "pyc_removed": removed_pyc,
    }
    report = venv_dir / "portable-venv-slim.json"
    # Write then count so after includes the report file itself.
    report.write_text("{}\n", encoding="utf-8")
    after = count_files(venv_dir)
    stats["venv_files_after"] = after
    stats["venv_files_removed"] = max(0, before - after)
    report.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats


def win_lib_ignore(_directory: str, names: Iterable[str]) -> list[str]:
    """shutil.copytree ignore for Windows python-home Lib/ (C11-A at materialize)."""
    skip = {"site-packages", "__pycache__", "idlelib", "turtledemo", "ensurepip", "test"}
    return [n for n in names if n in skip]
