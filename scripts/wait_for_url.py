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
        "--gate",
        action="store_true",
        help="Wait until JSON body has gate_ready=true (search gate may open)",
    )
    parser.add_argument(
        "--ready",
        action="store_true",
        help="Wait until JSON body has ready=true (for word-cache preload)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="With --ready: wait until startup_complete=true (all background preload)",
    )
    args = parser.parse_args()

    started = time.time()
    last_progress = -1.0
    near_done_pct = 85
    while time.time() - started < args.timeout:
        if args.gate or args.ready:
            payload = _fetch_json(args.url)
            if isinstance(payload, dict):
                if args.gate:
                    done = bool(payload.get("gate_ready"))
                    progress = float(
                        (payload.get("phases") or {}).get("word_cache", {}).get("progress")
                        or payload.get("progress")
                        or 0.0
                    )
                else:
                    done = bool(payload.get("startup_complete")) if args.full else bool(payload.get("ready"))
                    progress = float(payload.get("progress") or 0.0)
                if done:
                    pct = int(progress * 100) if progress else 100
                    print(f"[wait] 開得工！ ({pct}%)")
                    return 0
                if progress - last_progress >= 0.05 or last_progress < 0:
                    pct = int(progress * 100)
                    label = "差啲就齊" if pct >= near_done_pct else "執緊啲字"
                    print(f"[wait] {label}… {pct}%")
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
