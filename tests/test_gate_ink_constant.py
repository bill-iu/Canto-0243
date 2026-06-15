"""Regression: served gate script must define ink clip constant."""
from __future__ import annotations

import unittest
import urllib.request


class GateInkConstantTests(unittest.TestCase):
    def test_served_index_defines_gate_ink_clip_max(self):
        html = urllib.request.urlopen(
            "http://127.0.0.1:8000/frontend/index.html?boot=test-ink",
            timeout=5,
        ).read().decode("utf-8", "replace")
        self.assertIn("const GATE_INK_CLIP_MAX = 200", html)
        self.assertIn("if (canOpenSearchGate(data))", html)


if __name__ == "__main__":
    unittest.main()
