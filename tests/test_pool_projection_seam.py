"""接縫測試：runtime 近反義池讀取收口至 pool_projection。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

RUNTIME_MODULES = (
    REPO_ROOT / "app" / "services" / "relation_syntax_executor.py",
)

FORBIDDEN = ("build_pool",)
REQUIRED = ("pool_projection",)


class TestPoolProjectionSeam(unittest.TestCase):
    def test_runtime_services_do_not_import_build_pool(self):
        for path in RUNTIME_MODULES:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                for symbol in FORBIDDEN:
                    self.assertNotIn(symbol, source)
                for symbol in REQUIRED:
                    self.assertIn(symbol, source)


if __name__ == "__main__":
    unittest.main()
