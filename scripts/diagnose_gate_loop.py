#!/usr/bin/env python3
"""Replay frontend waitForPreloadReady against a cold-started server."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "debug-795493.log")
PRELOAD_TIMEOUT_MS = 30_000
POLL_MS = 220


def _log(hypothesis_id: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "795493",
        "hypothesisId": hypothesis_id,
        "location": "diagnose_gate_loop.py",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
        "runId": "diagnose-harness",
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"[DEBUG-gate] {message} {data}")


def _can_open(data: dict) -> bool:
    if data.get("ready") or data.get("gate_ready"):
        return True
    wc = (data.get("phases") or {}).get("word_cache") or {}
    return wc.get("status") in ("ready", "failed")


def _label(data: dict | None, connecting: bool = False) -> str:
    if connecting or not data:
        return "執緊啲字…"
    pct = int(max(0, min(100, round((data.get("progress") or 0) * 100))))
    wc_status = (data.get("phases") or {}).get("word_cache", {}).get("status")
    if data.get("ready") or wc_status == "ready":
        return "開得工！"
    if data.get("status") == "loading" or (data.get("progress") or 0) > 0:
        return f"執緊啲字… {pct}%" if pct < 85 else f"差啲就齊… {pct}%"
    return "執緊啲字…"


def _fetch_ready(base: str) -> dict:
    req = urllib.request.Request(f"{base}/ready", method="GET")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        if not (200 <= resp.status < 300):
            raise urllib.error.URLError(f"status {resp.status}")
        return json.loads(resp.read().decode())


def _wait_http(base: str, timeout_s: float = 120.0) -> float:
    started = time.perf_counter()
    while time.perf_counter() - started < timeout_s:
        try:
            req = urllib.request.Request(f"{base}/", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if 200 <= resp.status < 500:
                    return time.perf_counter() - started
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.35)
    raise TimeoutError("HTTP root never became reachable")


def simulate_gate_loop(base: str, *, open_delay_s: float) -> dict:
    """open_delay_s: seconds after spawn before gate polling starts (browser open lag)."""
    time.sleep(max(0.0, open_delay_s))
    budget_ms = PRELOAD_TIMEOUT_MS
    budget_active = False
    budget_last_at = 0.0
    last_snapshot: dict | None = None
    labels: list[str] = []
    poll = 0
    fail_streak = 0
    max_fail_streak = 0
    started = time.perf_counter()

    def pause_budget() -> None:
        nonlocal budget_active, budget_ms, budget_last_at
        if budget_active:
            budget_ms -= (time.perf_counter() - budget_last_at) * 1000.0
            budget_active = False

    def resume_budget() -> None:
        nonlocal budget_active, budget_last_at
        if not budget_active:
            budget_active = True
            budget_last_at = time.perf_counter()

    while True:
        poll += 1
        try:
            pause_budget()
            data = _fetch_ready(base)
            last_snapshot = data
            fail_streak = 0
            resume_budget()
            label = _label(data)
            labels.append(label)
            if poll <= 5 or _can_open(data) or poll % 10 == 0:
                _log(
                    "B",
                    "poll ok",
                    {
                        "poll": poll,
                        "elapsed_s": round(time.perf_counter() - started, 2),
                        "label": label,
                        "ready": data.get("ready"),
                        "status": data.get("status"),
                        "progress": data.get("progress"),
                        "gate_ready": data.get("gate_ready"),
                        "wc_status": (data.get("phases") or {}).get("word_cache", {}).get("status"),
                        "can_open": _can_open(data),
                        "budget_ms": round(budget_ms),
                    },
                )
            if _can_open(data):
                return {
                    "outcome": "success",
                    "polls": poll,
                    "elapsed_s": round(time.perf_counter() - started, 2),
                    "labels": labels[-5:],
                    "final": data,
                }
            budget_ms -= (time.perf_counter() - budget_last_at) * 1000.0
            budget_last_at = time.perf_counter()
            if budget_ms <= 0:
                return {
                    "outcome": "degraded",
                    "polls": poll,
                    "elapsed_s": round(time.perf_counter() - started, 2),
                    "labels": labels[-5:],
                    "max_fail_streak": max_fail_streak,
                    "last_snapshot": last_snapshot,
                }
        except Exception as e:
            pause_budget()
            fail_streak += 1
            max_fail_streak = max(max_fail_streak, fail_streak)
            if last_snapshot:
                labels.append(_label(last_snapshot))
            else:
                labels.append(_label(None, connecting=True))
            if poll <= 8 or poll % 10 == 0:
                _log(
                    "A",
                    "poll fail",
                    {
                        "poll": poll,
                        "elapsed_s": round(time.perf_counter() - started, 2),
                        "err": type(e).__name__,
                        "fail_streak": fail_streak,
                        "has_snapshot": last_snapshot is not None,
                        "budget_ms": round(budget_ms),
                    },
                )
        time.sleep(POLL_MS / 1000.0)

    return {
        "outcome": "incomplete",
        "polls": poll,
        "elapsed_s": round(time.perf_counter() - started, 2),
        "labels": labels[-5:],
        "max_fail_streak": max_fail_streak,
        "last_snapshot": last_snapshot,
    }


def main() -> int:
    port = int(os.environ.get("PORT", "8012"))
    host = os.environ.get("HOST", "127.0.0.1")
    open_delay = float(os.environ.get("OPEN_DELAY_S", "0"))
    base = f"http://{host}:{port}"
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["ENV"] = "local"

    subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "free_port.py"), "--port", str(port), "--host", host],
        cwd=ROOT,
        check=False,
    )

    _log("E", "spawning server", {"base": base})
    proc = subprocess.Popen([sys.executable, "main.py"], cwd=ROOT, env=env)
    try:
        if os.environ.get("SKIP_HTTP_WAIT") == "1":
            http_wait_s = 0.0
            _log("D", "skip http wait (immediate browser)", {})
            result = simulate_gate_loop(base, open_delay_s=open_delay)
        else:
            http_wait_s = _wait_http(base)
            _log("D", "http ready", {"seconds": round(http_wait_s, 3)})
            result = simulate_gate_loop(base, open_delay_s=open_delay)
        _log("C", "gate loop finished", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["outcome"] == "success" else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
