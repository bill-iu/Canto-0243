#!/usr/bin/env python3
"""E2E: 就緒閘應在 /ready 後解鎖搜尋（headless CDP via Playwright if installed）。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ready(base: str) -> dict:
    with urllib.request.urlopen(f"{base}/ready", timeout=3) as r:
        return json.loads(r.read().decode())


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[e2e] playwright not installed; skip browser e2e")
        return 0

    port = int(os.environ.get("PORT", "8015"))
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["ENV"] = "local"

    subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "free_port.py"), "--port", str(port)],
        cwd=ROOT,
        check=False,
    )
    proc = subprocess.Popen([sys.executable, "main.py"], cwd=ROOT, env=env)
    try:
        for _ in range(120):
            try:
                if _ready(base).get("ready"):
                    break
            except Exception:
                pass
            time.sleep(0.25)
        else:
            print("[e2e] FAIL backend never ready")
            return 1

        url = f"{base}/frontend/index.html?boot=e2e"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            deadline = time.time() + 20
            last_label = ""
            while time.time() < deadline:
                state = page.evaluate(
                    """() => ({
                      overlayHidden: document.getElementById('preloadOverlay')?.classList.contains('is-hidden'),
                      label: document.getElementById('preloadLabel')?.textContent || '',
                      searchDisabled: document.getElementById('searchInput')?.disabled,
                      fontsReady: document.documentElement.classList.contains('fonts-ready'),
                    })"""
                )
                last_label = state.get("label") or last_label
                if state.get("overlayHidden") and not state.get("searchDisabled"):
                    print("[e2e] PASS gate opened", json.dumps(state, ensure_ascii=False))
                    browser.close()
                    return 0
                time.sleep(0.3)
            print("[e2e] FAIL still gated", last_label)
            browser.close()
            return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
