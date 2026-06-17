"""TDD：近反義語法偵測（frontend/relation-syntax.mjs）。"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_TEST = REPO_ROOT / "tests" / "relation_syntax_test.mjs"


class TestRelationSyntaxJs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which("node")
        if cls.node is None:
            raise unittest.SkipTest("node not on PATH")

    def test_node_relation_syntax_tests_pass(self):
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
                "relation_syntax_test.mjs failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
