#!/usr/bin/env python3
"""Measure echo→HTML-ready time for 本機啟動 (maintainer manual bench)."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_SUFFIX = "/frontend/index.html"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bench local startup HTML readiness")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args()

    host, port = args.host, str(args.port)
    base = f"http://{host}:{port}"
    html_url = f"{base}{HTML_SUFFIX}"

    env = os.environ.copy()
    env["HOST"] = host
    env["PORT"] = port

    subprocess.run(
        [sys.executable, "scripts/free_port.py", "--port", port, "--host", host],
        cwd=ROOT,
        check=False,
    )

    started = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        rc = subprocess.run(
            [
                sys.executable,
                "scripts/wait_for_url.py",
                html_url,
                "--interval",
                "0.1",
                "--timeout",
                "120",
            ],
            cwd=ROOT,
            check=False,
        ).returncode
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if rc == 0:
            print(f"HTML ready in {elapsed_ms} ms ({html_url})")
            return 0
        print(f"Timeout after {elapsed_ms} ms ({html_url})", file=sys.stderr)
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
