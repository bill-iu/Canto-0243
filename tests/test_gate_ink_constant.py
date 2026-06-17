"""Regression: served gate modules must define ink clip constant."""
from __future__ import annotations

import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class GateInkConstantTests(unittest.TestCase):
    def test_served_index_defines_gate_ink_clip_max(self):
        base = "http://127.0.0.1:8000/frontend"
        html = urllib.request.urlopen(
            f"{base}/index.html?boot=test-ink",
            timeout=5,
        ).read().decode("utf-8", "replace")
        self.assertIn('src="./main.mjs"', html)
        ctx = urllib.request.urlopen(f"{base}/app-context.mjs", timeout=5).read().decode("utf-8", "replace")
        gate = urllib.request.urlopen(f"{base}/gate.mjs", timeout=5).read().decode("utf-8", "replace")
        self.assertIn("GATE_INK_CLIP_MAX = 200", ctx)
        self.assertIn("data.gate_ready", gate)


if __name__ == "__main__":
    unittest.main()
