"""D1: PWA process-level relation graph cache for derived_ant dual-open."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "client" / "src" / "db"
SCRIPT = REPO / "client" / "scripts" / "relation-graph-self-check.ts"


class RelationGraphPwaSeams(unittest.TestCase):
    def test_module_exports(self):
        src = (DB / "relation-graph.ts").read_text(encoding="utf-8")
        for sym in (
            "ensureRelationGraph",
            "invalidateRelationGraph",
            "isRelationGraphReady",
            "directSynNeighbors",
            "relationGraphBuildCount",
        ):
            with self.subTest(sym=sym):
                self.assertIn(sym, src)
        derived = (DB / "derived-ant.ts").read_text(encoding="utf-8")
        self.assertIn("ensureRelationGraph", derived)
        self.assertIn("directSynNeighbors", derived)
        init = (DB / "init.ts").read_text(encoding="utf-8")
        self.assertIn("invalidateRelationGraph", init)

    def test_node_self_check(self):
        if not SCRIPT.is_file():
            self.skipTest("self-check script missing")
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        tsx = REPO / "client" / "node_modules" / "tsx" / "dist" / "cli.mjs"
        npx = shutil.which("npx")
        if tsx.is_file():
            cmd = [node, str(tsx), str(SCRIPT)]
        elif npx:
            cmd = [npx, "--yes", "tsx", str(SCRIPT)]
        else:
            cmd = [node, "--import", "tsx", str(SCRIPT)]
        proc = subprocess.run(
            cmd,
            cwd=REPO / "client",
            capture_output=True,
            text=True,
            check=False,
        )
        err = (proc.stderr or "") + (proc.stdout or "")
        if proc.returncode != 0 and (
            "Cannot find package" in err
            or "not found" in err.lower()
            or "ENOENT" in err
        ):
            self.skipTest(f"tsx unavailable: {err[:200]}")
        self.assertEqual(proc.returncode, 0, msg=err)
        self.assertIn("relation-graph-self-check ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
