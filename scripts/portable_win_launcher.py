#!/usr/bin/env python3
"""Windows portable GUI entry — PyInstaller --onefile -w (build-time only)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _win_message(title: str, text: str) -> None:
    if sys.platform != "win32":
        print(f"{title}: {text}", file=sys.stderr)
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    except Exception:
        print(f"{title}: {text}", file=sys.stderr)


def _ensure_env_local(root: Path) -> None:
    """Align with START.bat: first launch seeds .env.local from env.portable."""
    env_local = root / ".env.local"
    env_portable = root / "env.portable"
    if not env_local.is_file() and env_portable.is_file():
        shutil.copy2(env_portable, env_local)


def _patch_pyvenv_home(root: Path) -> None:
    """Point pyvenv.cfg home at this extract (build-machine paths break on other PCs, #66)."""
    # Frozen PyInstaller has no scripts/ on sys.path — keep patch inline.
    cfg = root / "venv" / "pyvenv.cfg"
    home = (root / "venv" / "python-home").resolve()
    if not cfg.is_file() or not (home / "python.exe").is_file():
        return
    lines = [
        f"home = {home}" if line.startswith("home = ") else line
        for line in cfg.read_text(encoding="utf-8").splitlines()
    ]
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_python(root: Path) -> Path | None:
    for name in ("pythonw.exe", "python.exe"):
        candidate = root / "venv" / "Scripts" / name
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    root = _bundle_root()
    os.chdir(root)

    if not (root / "lyrics.db").is_file():
        _win_message("Canto-0243", "找不到 lyrics.db。請確認已完整解壓套件。")
        return 1

    python = _resolve_python(root)
    if python is None:
        _win_message("Canto-0243", "找不到內建執行環境。請重新下載完整免安裝套件。")
        return 1

    _patch_pyvenv_home(root)
    _ensure_env_local(root)

    env = os.environ.copy()
    env.setdefault("PORTABLE", "1")
    env.setdefault("ENV", "local")

    kwargs: dict = {
        "cwd": root,
        "env": env,
        "check": False,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    rc = subprocess.run(
        [
            str(python),
            "scripts/local_launch.py",
            "--portable",
            "--gui",
            "--python",
            str(python),
            "--root",
            str(root),
        ],
        **kwargs,
    ).returncode

    if rc != 0:
        _win_message(
            "Canto-0243",
            "查韻介面未能啟動。\n\n"
            "請確認已完整解壓套件；或雙擊 START.bat 查看詳情。\n"
            "若 8000 埠被佔用，請編輯 .env.local 修改 PORT。",
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
