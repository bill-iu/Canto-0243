#!/usr/bin/env python3
"""Poll until an HTTP URL responds (startup scripts wait for backend or preload)."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _fetch_json(url: str, timeout: float = 2.0) -> dict | None:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if not (200 <= resp.status < 500):
                return None
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return None


def _fetch_status(url: str, timeout: float = 2.0) -> int | None:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until URL is reachable (optionally /ready)")
    parser.add_argument("url", help="e.g. http://127.0.0.1:8000/ or http://127.0.0.1:8000/ready")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=0.35)
    parser.add_argument(
        "--ready",
        action="store_true",
        help="Wait until JSON body has ready=true (for word-cache preload)",
    )
    args = parser.parse_args()

    started = time.time()
    last_progress = -1.0
    while time.time() - started < args.timeout:
        if args.ready:
            payload = _fetch_json(args.url)
            if isinstance(payload, dict):
                if payload.get("ready"):
                    pct = int(float(payload.get("progress") or 1.0) * 100)
                    print(f"[wait] 詞庫就緒 ({pct}%)")
                    return 0
                progress = float(payload.get("progress") or 0.0)
                if progress - last_progress >= 0.05 or last_progress < 0:
                    pct = int(progress * 100)
                    status = payload.get("status") or "loading"
                    print(f"[wait] 載入詞庫… {pct}% ({status})")
                    last_progress = progress
        else:
            status = _fetch_status(args.url)
            if status is not None and 200 <= status < 500:
                return 0
        time.sleep(args.interval)

    elapsed_ms = int((time.time() - started) * 1000)
    print(f"[wait] Timeout after {elapsed_ms} ms ({args.url})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
