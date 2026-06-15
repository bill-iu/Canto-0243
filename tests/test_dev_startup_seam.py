"""接縫測試：開發版啟動 — HTML 可載入後才開瀏覽器，不等 gate。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
START_SH = REPO_ROOT / "start.sh"


class TestDevStartupSeam(unittest.TestCase):
    def test_start_sh_waits_for_frontend_html_before_open(self):
        source = START_SH.read_text(encoding="utf-8")
        open_idx = source.find('open "$URL"')
        if open_idx < 0:
            open_idx = source.find('xdg-open "$URL"')
        self.assertGreater(open_idx, 0, "start.sh should open browser with URL")
        before_open = source[:open_idx]
        self.assertIn("frontend/index.html", before_open)
        self.assertIn("wait_for_url.py", before_open)
        self.assertNotIn("仍嘗試打開瀏覽器", source)

    def test_start_sh_does_not_wait_gate_before_open(self):
        source = START_SH.read_text(encoding="utf-8")
        gate_idx = source.find("--gate")
        open_idx = min(
            i for i in (
                source.find('open "$URL"'),
                source.find('xdg-open "$URL"'),
                source.find('cmd //c start'),
            )
            if i >= 0
        )
        self.assertGreater(gate_idx, 0)
        self.assertGreater(open_idx, 0)
        self.assertGreater(gate_idx, open_idx, "--gate wait should run after browser open")


if __name__ == "__main__":
    unittest.main()
