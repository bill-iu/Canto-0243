#!/usr/bin/env python3
"""Unified local launch — CONTEXT § 本機啟動."""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HTML_SUFFIX = "/frontend/index.html"
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
        }
    return {
        "starting": "正在啟動 Canto-0243… 查韻介面就緒後將開啟瀏覽器。",
        "opening": "正在打開查韻介面…",
        "wait_fail": "查韻介面尚未就緒，請稍後手動打開：",
        "running": "後端：",
        "ui": "前端：",
        "close_hint": "關閉請按 Ctrl+C",
    }


def _win_no_window_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _headless_python(python: Path) -> Path:
    """ponytail: Windows 用 pythonw.exe 跑背景子行程，避免彈 CMD。"""
    if sys.platform != "win32":
        return python
    pythonw = python.with_name("pythonw.exe")
    return pythonw if pythonw.is_file() else python


def _spawn_detached(python: Path, root: Path, args: list[str]) -> None:
    kwargs: dict = {
        "cwd": root,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
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
    args = parser.parse_args()

    root = (args.root or Path.cwd()).resolve()
    os.chdir(root)
    python = (args.python or Path(sys.executable)).resolve()
    msgs = _messages(args.lang)

    print(msgs["starting"], flush=True)
    if args.portable:
        print(msgs["close_hint"], flush=True)

    host = os.environ.get("HOST", "127.0.0.1")
    port = os.environ.get("PORT", "8000")
    _run_quiet(
        python,
        root,
        ["scripts/free_port.py", "--port", port, "--host", host],
    )

    env = os.environ.copy()
    env["HOST"] = host
    env["PORT"] = port
    if args.portable:
        env["PORTABLE"] = "1"
        env.setdefault("ENV", "local")

    server_kwargs: dict = {
        "cwd": root,
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        server_kwargs["creationflags"] = _win_no_window_flags()
    server = subprocess.Popen([str(_headless_python(python)), "main.py"], **server_kwargs)

    def _on_signal(signum: int, _frame: object) -> None:
        _terminate(server)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    base_url = f"http://{host}:{port}"
    html_url = f"{base_url}{HTML_SUFFIX}"
    boot_url = f"{html_url}?boot={int(time.time())}"

    html_ready = _run_quiet(
        python,
        root,
        [
            "scripts/wait_for_url.py",
            html_url,
            "--interval",
            WAIT_INTERVAL,
            "--timeout",
            WAIT_TIMEOUT,
        ],
    ) == 0

    if html_ready:
        print(msgs["opening"], flush=True)
        webbrowser.open(boot_url, new=2)
    else:
        print(f"{msgs['wait_fail']} {boot_url}", flush=True)

    _spawn_detached(
        python,
        root,
        ["scripts/wait_for_url.py", "--gate", f"{base_url}/ready"],
    )
    if args.tail_ready:
        _spawn_detached(
            python,
            root,
            ["scripts/wait_for_url.py", "--ready", "--full", f"{base_url}/ready"],
        )

    print(f"{msgs['running']} {base_url}")
    print(f"{msgs['ui']} {boot_url}")

    wait_server = bool(args.wait_server) or not args.no_wait_server

    exit_code = 0
    if wait_server:
        exit_code = server.wait()
    elif server.poll() is not None:
        exit_code = server.returncode or 1

    if args.pause_on_exit and sys.platform == "win32":
        try:
            input("Press Enter to close...")
        except EOFError:
            pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
