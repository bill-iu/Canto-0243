"""PyApp / Desktop GUI entry (ADR-0068).

Resolves the payload root via app.payload_root SSOT, binds CANTO_PAYLOAD_ROOT,
then runs local_launch in --gui mode. Backend may outlive this process (A1).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


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
    # Import only payload_root before bind — never app.db / lexicon first.
    from app.payload_root import bind_payload_root, resolve_payload_root

    root = resolve_payload_root()
    os.chdir(root)
    bind_payload_root(root)
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
