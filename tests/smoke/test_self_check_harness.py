"""C9 self-check harness: list + tag filter (no full suite)."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLIENT = REPO / "client"
HARNESS = CLIENT / "scripts" / "self-check-harness.mjs"


class SelfCheckHarnessTests(unittest.TestCase):
    def test_list_includes_ci_checks(self):
        proc = subprocess.run(
            ["node", str(HARNESS), "--list", "--tag", "ci"],
            cwd=CLIENT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        out = proc.stdout
        self.assertIn("guide-examples", out)
        self.assertIn("portable-host-build", out)

    def test_manifest_scripts_exist(self):
        data = json.loads(
            (CLIENT / "scripts" / "self-check-manifest.json").read_text(encoding="utf-8")
        )
        for check in data["checks"]:
            path = CLIENT / "scripts" / check["script"]
            with self.subTest(id=check["id"]):
                self.assertTrue(path.is_file(), msg=check["script"])


if __name__ == "__main__":
    unittest.main()
