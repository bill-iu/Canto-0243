#!/usr/bin/env python3
"""Release TCP listen port before startup (start.sh / START.sh)."""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys


def _listening_pids(port: int) -> list[int]:
    if sys.platform == "win32":
        return _listening_pids_windows(port)
    return _listening_pids_unix(port)


def _listening_pids_windows(port: int) -> list[int]:
    # Prefer Get-NetTCPConnection (accurate OwningProcess); netstat can show stale PIDs.
    ps_cmd = (
        f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
        f" | Select-Object -ExpandProperty OwningProcess -Unique"
    )
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        pids = {int(line.strip()) for line in out.splitlines() if line.strip().isdigit()}
        if pids:
            return sorted(pid for pid in pids if pid > 4)
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass

    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    pids: set[int] = set()
    needle = f":{port}"
    for line in out.splitlines():
        upper = line.upper()
        if needle not in line or "LISTENING" not in upper:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 4:
            pids.add(pid)
    return sorted(pids)


def _canto_main_pids(project_root: str) -> list[int]:
    """Windows: end stray uvicorn/main.py from prior start.sh runs (reload orphans)."""
    if sys.platform != "win32":
        return []
    del project_root  # reserved for future cwd-based filtering
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    pids: set[int] = set()
    for line in out.splitlines():
        lower = line.lower()
        if "main.py" not in lower:
            continue
        if " -c " in lower or 'python" -c' in lower:
            continue
        parts = [p.strip() for p in line.split(",") if p.strip()]
        for token in reversed(parts):
            if token.isdigit():
                pid = int(token)
                if pid > 4:
                    pids.add(pid)
                break
    return sorted(pids)


def _listening_pids_unix(port: int) -> list[int]:
    for cmd in (
        ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
        ["lsof", "-ti", f":{port}"],
    ):
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        pids: list[int] = []
        for token in out.replace("\n", " ").split():
            try:
                pid = int(token)
            except ValueError:
                continue
            if pid > 1:
                pids.append(pid)
        if pids:
            return sorted(set(pids))
    return []


def _terminate(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Free listen port before Canto-0243 startup")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument(
        "--project-root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Also terminate stray main.py from this repo (Windows reload orphans)",
    )
    args = parser.parse_args()

    own_pid = os.getpid()
    for attempt in range(3):
        pids = {pid for pid in _listening_pids(args.port) if pid != own_pid}
        pids.update(_canto_main_pids(args.project_root))
        pids.discard(own_pid)
        if not pids:
            break
        for pid in sorted(pids):
            print(f"[free_port] 釋放 port {args.port}（結束 PID {pid}）")
            _terminate(pid)
        if attempt < 2:
            import time

            time.sleep(0.6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
