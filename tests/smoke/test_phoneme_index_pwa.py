"""P1: PWA phoneme index module exists + layout seams; node self-check when available."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PM = REPO / "client" / "src" / "db" / "position-match"
SCRIPT = REPO / "client" / "scripts" / "phoneme-index-self-check.ts"


class PhonemeIndexPwaSeams(unittest.TestCase):
    def test_module_exports(self):
        src = (PM / "phoneme-index.ts").read_text(encoding="utf-8")
        for sym in (
            "ensurePhonemeIndex",
            "getPhonemeIndexCandidates",
            "invalidatePhonemeIndex",
            "isPhonemeIndexReady",
        ):
            with self.subTest(sym=sym):
                self.assertIn(sym, src)
        engine = (PM / "engine.ts").read_text(encoding="utf-8")
        self.assertIn("getPhonemeAnchorCandidates", engine)
        sources = (PM / "sources.ts").read_text(encoding="utf-8")
        self.assertIn("getPhonemeAnchorCandidates", sources)
        init = (REPO / "client" / "src" / "db" / "init.ts").read_text(encoding="utf-8")
        self.assertIn("invalidatePhonemeIndex", init)

    def test_node_self_check(self):
        if not SCRIPT.is_file():
            self.skipTest("self-check script missing")
        fixture = REPO / "tests" / "fixtures" / "lyrics.db"
        if not fixture.is_file():
            self.skipTest("fixture db missing")
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        # Prefer local tsx, then npx tsx (matches other client self-checks)
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
        self.assertIn("phoneme-index-self-check ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
