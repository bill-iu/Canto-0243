#!/usr/bin/env python3
"""Windows portable runtime — materialize build-machine Python into venv/python-home (#66)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

_WIN_RUNTIME_FILES = (
    "python.exe",
    "pythonw.exe",
    "python3.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
)


def windows_python_home(venv_dir: Path) -> Path:
    """Bundled base prefix used as pyvenv.cfg home on Windows."""
    return venv_dir / "python-home"


def patch_windows_pyvenv_home(bundle_root: str | Path) -> bool:
    """Rewrite venv/pyvenv.cfg home to this extract's python-home (any path)."""
    root = Path(bundle_root).resolve()
    cfg = root / "venv" / "pyvenv.cfg"
    home = windows_python_home(root / "venv").resolve()
    if not cfg.is_file() or not (home / "python.exe").is_file():
        return False
    lines: list[str] = []
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if line.startswith("home = "):
            lines.append(f"home = {home}")
        else:
            lines.append(line)
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _parse_pyvenv_cfg(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if " = " not in line:
            continue
        key, value = line.split(" = ", 1)
        out[key.strip()] = value.strip()
    return out


def _source_prefix(cfg: dict[str, str], home: Path) -> Path | None:
    base = cfg.get("base-prefix")
    if base:
        candidate = Path(base)
        if candidate.is_dir():
            return candidate
    # Windows installs: home is the prefix root (python.exe + Lib + DLLs).
    if (home / "python.exe").is_file() or (home / "Lib").is_dir():
        return home if home.is_dir() else None
    parent = home.parent
    return parent if parent.is_dir() else None


def _home_under_venv(home: Path, venv_dir: Path) -> bool:
    try:
        home.resolve().relative_to(venv_dir.resolve())
        return True
    except ValueError:
        return False


def materialize_windows_python_home(venv_dir: Path) -> None:
    """Copy base CPython into venv/python-home and point pyvenv.cfg home there.

    Windows venv Scripts/python.exe is a redirector that requires
    ``{home}\\python.exe`` — stdlib-only copies are not enough (#66).
    """
    if sys.platform != "win32":
        return
    venv_dir = venv_dir.resolve()
    cfg_path = venv_dir / "pyvenv.cfg"
    if not cfg_path.is_file():
        return
    text = cfg_path.read_text(encoding="utf-8")
    cfg = _parse_pyvenv_cfg(text)
    home_raw = cfg.get("home")
    if not home_raw:
        return
    home = Path(home_raw)
    py_home = windows_python_home(venv_dir)
    if _home_under_venv(home, venv_dir) and (home / "python.exe").is_file():
        return

    src = _source_prefix(cfg, home)
    if src is None:
        raise RuntimeError(f"cannot locate Windows Python prefix for portable venv: {cfg_path}")

    if py_home.exists():
        shutil.rmtree(py_home)
    py_home.mkdir(parents=True)

    for name in _WIN_RUNTIME_FILES:
        src_f = src / name
        if src_f.is_file():
            shutil.copy2(src_f, py_home / name)
    ver_dll = src / f"python{sys.version_info.major}{sys.version_info.minor}.dll"
    if ver_dll.is_file():
        shutil.copy2(ver_dll, py_home / ver_dll.name)
    for dll in src.glob("python*.dll"):
        dest = py_home / dll.name
        if not dest.is_file():
            shutil.copy2(dll, dest)

    src_dlls = src / "DLLs"
    if src_dlls.is_dir():
        shutil.copytree(src_dlls, py_home / "DLLs", dirs_exist_ok=True)

    src_lib = src / "Lib"
    if src_lib.is_dir():
        try:
            from portable_venv_slim import win_lib_ignore
        except ImportError:  # pragma: no cover
            from scripts.portable_venv_slim import win_lib_ignore

        shutil.copytree(
            src_lib,
            py_home / "Lib",
            dirs_exist_ok=True,
            ignore=win_lib_ignore,
        )

    if not (py_home / "python.exe").is_file():
        raise RuntimeError(f"materialize failed: missing {py_home / 'python.exe'}")

    resolved = py_home.resolve()
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("home = "):
            lines.append(f"home = {resolved}")
        else:
            lines.append(line)
    cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
