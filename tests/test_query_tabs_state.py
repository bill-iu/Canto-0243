"""TDD：查詢分頁狀態機（frontend/query-tabs-state.mjs）。"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_MODULE = REPO_ROOT / "frontend" / "query-tabs-state.mjs"
NODE_TEST = REPO_ROOT / "tests" / "query_tabs_state_test.mjs"


class TestQueryTabsStateJs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which("node")
        if cls.node is None:
            raise unittest.SkipTest("node not on PATH")

    def test_state_module_exists(self):
        self.assertTrue(
            STATE_MODULE.is_file(),
            f"missing {STATE_MODULE.relative_to(REPO_ROOT)}",
        )

    def test_node_state_tests_pass(self):
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
                "query_tabs_state_test.mjs failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
