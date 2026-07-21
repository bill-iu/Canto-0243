"""PyApp / Desktop GUI entry (ADR-0068).

Resolves the payload root (sidecar lyrics.db + product UI), then runs
local_launch in --gui mode. Backend may outlive this process (A1).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_payload_root() -> Path:
    """Desktop sidecar root: env, else directory next to launcher, else cwd."""
    env = os.environ.get("CANTO_PAYLOAD_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()

    # PyApp sets PYAPP=1; frozen/other launchers may set sys.executable to the exe.
    if os.environ.get("PYAPP") == "1" or getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    cwd = Path.cwd().resolve()
    if (cwd / "lyrics.db").is_file() and (
        (cwd / "client" / "dist-portable" / "index.html").is_file()
        or (cwd / "main.py").is_file()
    ):
        return cwd

    # Dev: package lives under repo/app/
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "lyrics.db").is_file() and (parent / "app").is_dir():
            return parent
    return cwd


def _win_message(title: str, text: str) -> None:
    if sys.platform != "win32":
        print(f"{title}: {text}", file=sys.stderr)
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    except Exception:
        print(f"{title}: {text}", file=sys.stderr)


def main() -> int:
    root = resolve_payload_root()
    os.chdir(root)
    os.environ["CANTO_PAYLOAD_ROOT"] = str(root)
    os.environ.setdefault("PORTABLE", "1")
    os.environ.setdefault("ENV", "local")

    if not (root / "lyrics.db").is_file():
        _win_message(
            "Canto-0243",
            "找不到 lyrics.db。\n\n"
            "請確認已完整解壓 Desktop 套件（詞庫須與 launcher 同目錄）。\n"
            "Missing lyrics.db next to the launcher — re-extract the full package.",
        )
        return 1

    ui = root / "client" / "dist-portable" / "index.html"
    if not ui.is_file():
        _win_message(
            "Canto-0243",
            "找不到查韻介面（client/dist-portable）。\n\n"
            "請重新下載完整 Desktop 套件並完整解壓。",
        )
        return 1

    from app.launch.local_launch import main as launch_main

    # local_launch reads sys.argv — inject GUI flags.
    sys.argv = [
        "canto-0243",
        "--portable",
        "--gui",
        "--python",
        sys.executable,
        "--root",
        str(root),
    ]
    try:
        return int(launch_main())
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    except Exception as exc:
        _win_message("Canto-0243", f"查韻介面未能啟動。\n\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
