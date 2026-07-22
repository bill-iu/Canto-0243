#!/usr/bin/env python3
"""Unified local launch — CONTEXT § 本機啟動."""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HTML_SUFFIX = "/app/index.html"
APP_UI_REL = Path("client") / "dist-portable"
APP_UI_INDEX = APP_UI_REL / "index.html"
WAIT_INTERVAL = "0.1"
WAIT_TIMEOUT = "90"


def _messages(lang: str) -> dict[str, str]:
    if lang == "en":
        return {
            "starting": "Starting Canto-0243... Browser opens when the UI is ready.",
            "opening": "Opening Canto-0243 in your browser...",
            "wait_fail": "UI not ready yet. Open manually:",
            "running": "Backend:",
            "ui": "UI:",
            "close_hint": "Close this window or press Ctrl+C to stop.",
            "building_ui": "Portable UI missing — running: cd client && npm run build:portable …",
            "ui_missing": (
                "Product UI not found (client/dist-portable/index.html).\n\n"
                "Dev checkout: cd client && npm run build:portable\n"
                "Desktop package: re-download the full package (UI must be inside the zip)."
            ),
            "checking_update": "Checking for desktop package updates…",
        }
    return {
        "starting": "正在啟動 Canto-0243… 查韻介面就緒後將開啟瀏覽器。",
        "opening": "正在打開查韻介面…",
        "wait_fail": "查韻介面尚未就緒，請稍後手動打開：",
        "running": "後端：",
        "ui": "前端：",
        "close_hint": "關閉請按 Ctrl+C",
        "building_ui": "未找到查韻介面，正在建置：cd client && npm run build:portable …",
        "ui_missing": (
            "找不到產品介面（client/dist-portable/index.html）。\n\n"
            "開發目錄：請先執行 cd client && npm run build:portable\n"
            "Desktop 套件：請重新下載完整 zip（套件內須含查韻介面）。"
        ),
        "checking_update": "正在檢查套件更新…",
    }


def _win_no_window_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def app_ui_ready(root: Path) -> bool:
    return (root / APP_UI_INDEX).is_file()


def _app_ui_stale(root: Path) -> bool:
    """True when source UI is newer than dist-portable (dev checkout only)."""
    index = root / APP_UI_INDEX
    if not index.is_file():
        return True
    dist_mtime = index.stat().st_mtime
    markers = (
        root / "client" / "src" / "App.tsx",
        root / "client" / "src" / "mode-menu.tsx",
        root / "client" / "src" / "pwa-app.css",
        root / "client" / "index.html",
        root / "shared" / "open-design.css",
        root / "shared" / "chrome-tabs.css",
        root / "shared" / "shell.css",
        root / "shared" / "ready-gate.css",
    )
    return any(p.is_file() and p.stat().st_mtime > dist_mtime for p in markers)


def _npm_cmd() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


def try_build_portable_ui(root: Path, *, silent: bool = False) -> bool:
    """Build client/dist-portable when this is a source checkout with npm."""
    client = root / "client"
    if not (client / "package.json").is_file():
        return False
    npm = _npm_cmd()
    if not npm:
        return False
    kwargs: dict = {"cwd": client, "check": False}
    if silent:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
        if sys.platform == "win32":
            kwargs["creationflags"] = _win_no_window_flags()
    rc = subprocess.run([npm, "run", "build:portable"], **kwargs).returncode
    return rc == 0 and app_ui_ready(root)


def ensure_app_ui(root: Path, *, lang: str = "zh", silent: bool = False) -> None:
    """Guarantee product UI exists (and is fresh) before starting main.py."""
    msgs = _messages(lang)
    needs_build = not app_ui_ready(root) or _app_ui_stale(root)
    if not needs_build:
        return
    if not silent:
        print(msgs["building_ui"], flush=True)
    if try_build_portable_ui(root, silent=silent):
        return
    if app_ui_ready(root):
        # Stale rebuild failed but an older dist exists — keep going.
        return
    raise SystemExit(msgs["ui_missing"])


def _python_exe(path: Path | str | None = None) -> Path:
    """Absolute path to a Python interpreter **without** following symlinks.

    PyApp/uv venv ``bin/python`` is a symlink into the distribution cache.
    ``Path.resolve()`` follows it and breaks ``python -m app…`` (no site-packages).
    """
    p = Path(path or sys.executable)
    if not p.is_absolute():
        p = Path.cwd() / p
    # absolute() keeps venv symlink; resolve() would collapse to base_prefix python
    return p.absolute()


def _headless_python(python: Path) -> Path:
    """ponytail: Windows 用 pythonw.exe 跑背景子行程，避免彈 CMD。"""
    if sys.platform != "win32":
        return python
    pythonw = python.with_name("pythonw.exe")
    return pythonw if pythonw.is_file() else python


def _tool_argv(tool: str) -> list[str]:
    """Prefer installed modules (wheel); fall back to scripts/*.py in a checkout."""
    return ["-m", f"app.launch.{tool}"]


def _server_argv(root: Path) -> list[str]:
    """Checkout keeps main.py on disk; Desktop wheel runs main as a module."""
    if (root / "main.py").is_file():
        return ["main.py"]
    return ["-m", "main"]


def _spawn_detached(
    python: Path,
    root: Path,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> None:
    kwargs: dict = {
        "cwd": root,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if env is not None:
        kwargs["env"] = env
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | _win_no_window_flags()
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([str(_headless_python(python)), *args], **kwargs)


def _run_quiet(python: Path, root: Path, args: list[str]) -> int:
    kwargs: dict = {"cwd": root, "check": False}
    if sys.platform == "win32":
        kwargs["creationflags"] = _win_no_window_flags()
    return subprocess.run([str(python), *args], **kwargs).returncode


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _html_ready(python: Path, root: Path, html_url: str, *, timeout: str = WAIT_TIMEOUT) -> bool:
    return (
        _run_quiet(
            python,
            root,
            [
                *_tool_argv("wait_for_url"),
                html_url,
                "--interval",
                WAIT_INTERVAL,
                "--timeout",
                timeout,
            ],
        )
        == 0
    )


def _open_browser(boot_url: str) -> None:
    webbrowser.open(boot_url, new=2)


def _probe_home_portable(base_url: str) -> bool | None:
    """若後端已在跑，回傳 portable 旗標；連線失敗則 None。"""
    try:
        import json
        import urllib.error
        import urllib.request

        with urllib.request.urlopen(f"{base_url.rstrip('/')}/", timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            return bool(data.get("portable"))
    except Exception:
        return None


def _maybe_check_portable_update(root: Path, *, lang: str, silent: bool) -> None:
    """ADR-0059: short timeout fingerprint check; fail-open; terminal notice."""
    try:
        from app.portable_update import check_update, format_terminal_notice
    except Exception:
        return
    msgs = _messages(lang)
    if not silent:
        print(msgs.get("checking_update", ""), flush=True)
    try:
        status = check_update(root, timeout=2.0)
    except Exception:
        return
    notice = format_terminal_notice(status, lang=lang)
    if notice and not silent:
        print(notice, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Canto-0243 local launch (start.sh / START.*)")
    parser.add_argument("--root", type=Path, default=None, help="Repo / portable bundle root")
    parser.add_argument("--python", type=Path, default=None, help="Python executable")
    parser.add_argument("--lang", choices=("en", "zh"), default="zh")
    parser.add_argument("--portable", action="store_true", help="Set PORTABLE=1 for child main.py")
    parser.add_argument(
        "--wait-server",
        action="store_true",
        help="Block until main.py exits (portable default)",
    )
    parser.add_argument(
        "--no-wait-server",
        action="store_true",
        help="Return after opening browser (dev start.sh background job)",
    )
    parser.add_argument(
        "--tail-ready",
        action="store_true",
        help="Background-wait for full startup_complete (dev)",
    )
    parser.add_argument(
        "--pause-on-exit",
        action="store_true",
        help="Windows: pause before exit (START.bat)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="No terminal output (Windows GUI launcher)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Portable GUI: silent, no-wait-server, reuse running backend",
    )
    args = parser.parse_args()

    if args.gui:
        args.silent = True
        args.no_wait_server = True
        args.portable = True

    root = (args.root or Path.cwd()).resolve()
    os.chdir(root)
    python = _python_exe(args.python)
    msgs = _messages(args.lang)

    host = os.environ.get("HOST", "127.0.0.1")
    port = os.environ.get("PORT", "8000")
    base_url = f"http://{host}:{port}"
    html_url = f"{base_url}{HTML_SUFFIX}"
    boot_url = f"{html_url}?boot={int(time.time())}"

    # Reuse only when an already-running backend is ours (portable=true).
    # `is not False` was too loose: connection/JSON miss → None → false success (exit 0).
    if args.gui and _html_ready(python, root, html_url, timeout="1"):
        if _probe_home_portable(base_url) is True:
            if args.portable:
                _maybe_check_portable_update(root, lang=args.lang, silent=args.silent)
            _open_browser(boot_url)
            return 0

    # Product UI is /app (client/dist-portable). Build on demand for source checkouts.
    ensure_app_ui(root, lang=args.lang, silent=args.silent)

    if args.portable:
        _maybe_check_portable_update(root, lang=args.lang, silent=args.silent)

    if not args.silent:
        print(msgs["starting"], flush=True)
        if args.portable:
            print(msgs["close_hint"], flush=True)

    _run_quiet(
        python,
        root,
        [*_tool_argv("free_port"), "--port", port, "--host", host],
    )

    env = os.environ.copy()
    env["HOST"] = host
    env["PORT"] = port
    env.setdefault("CANTO_PAYLOAD_ROOT", str(root))
    if args.portable:
        env["PORTABLE"] = "1"
        env.setdefault("ENV", "local")

    server_argv = _server_argv(root)
    server: subprocess.Popen[bytes] | None = None
    if args.gui:
        # ponytail: detach so launcher exit does not reap main (A1 / ADR-0068)
        _spawn_detached(python, root, server_argv, env=env)
    else:
        server_kwargs: dict = {
            "cwd": root,
            "env": env,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            server_kwargs["creationflags"] = _win_no_window_flags()
        server = subprocess.Popen(
            [str(_headless_python(python)), *server_argv],
            **server_kwargs,
        )

        def _on_signal(signum: int, _frame: object) -> None:
            assert server is not None
            _terminate(server)
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGINT, _on_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _on_signal)

    html_ready = _html_ready(python, root, html_url)

    if html_ready:
        if not args.silent:
            print(msgs["opening"], flush=True)
        _open_browser(boot_url)
    elif not args.silent:
        print(f"{msgs['wait_fail']} {boot_url}", flush=True)

    if args.gui:
        _spawn_detached(
            python,
            root,
            [*_tool_argv("wait_for_url"), "--gate", f"{base_url}/ready"],
        )
        return 0 if html_ready else 1

    _spawn_detached(
        python,
        root,
        [*_tool_argv("wait_for_url"), "--gate", f"{base_url}/ready"],
    )
    if args.tail_ready:
        _spawn_detached(
            python,
            root,
            [*_tool_argv("wait_for_url"), "--ready", "--full", f"{base_url}/ready"],
        )

    if not args.silent:
        print(f"{msgs['running']} {base_url}")
        print(f"{msgs['ui']} {boot_url}")

    wait_server = bool(args.wait_server) or not args.no_wait_server

    exit_code = 0
    if wait_server and server is not None:
        exit_code = server.wait()
    elif server is not None and server.poll() is not None:
        exit_code = server.returncode or 1
    elif not html_ready:
        exit_code = 1

    if args.pause_on_exit and sys.platform == "win32":
        try:
            input("Press Enter to close...")
        except EOFError:
            pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
