"""TDD：搜尋結果導航（frontend/search-navigation.mjs）。"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NAV_MODULE = REPO_ROOT / "frontend" / "search-navigation.mjs"
NODE_TEST = REPO_ROOT / "tests" / "search_navigation_test.mjs"


class TestSearchNavigationJs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which("node")
        if cls.node is None:
            raise unittest.SkipTest("node not on PATH")

    def test_navigation_module_exists(self):
        self.assertTrue(
            NAV_MODULE.is_file(),
            f"missing {NAV_MODULE.relative_to(REPO_ROOT)}",
        )

    def test_node_navigation_tests_pass(self):
        proc = subprocess.run(
            [self.node, "--test", str(NODE_TEST)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            self.fail(
                "search_navigation_test.mjs failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )


if __name__ == "__main__":
    unittest.main()