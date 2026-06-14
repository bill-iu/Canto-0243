#!/usr/bin/env python3
"""Poll until an HTTP URL responds (startup scripts wait for backend)."""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until URL is reachable")
    parser.add_argument("url", help="e.g. http://127.0.0.1:8000/")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=0.35)
    args = parser.parse_args()

    started = time.time()
    while time.time() - started < args.timeout:
        try:
            req = urllib.request.Request(args.url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if 200 <= resp.status < 500:
                    return 0
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(args.interval)

    elapsed_ms = int((time.time() - started) * 1000)
    print(f"[wait] Timeout after {elapsed_ms} ms ({args.url})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
