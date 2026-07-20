"""Phase C PR4: TS 近反義池 project → build → ranking (grill C4 + Phase 4 pool locality)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "client" / "src" / "db"
MAX_LINES = 350


class PhaseCPr4RelationPoolSplit(unittest.TestCase):
    def test_module_layout(self):
        expected = {
            "relation-pool-ranking.ts": ("finalScore", "mergeRelationPools", "sortSynPool", "sortAntPool"),
            "relation-pool-builder.ts": ("buildRelationPool", "fetchDbRelations"),
            "relation-pool-projection.ts": ("projectRelationPool", "relationPoolPage"),
        }
        for name, symbols in expected.items():
            path = DB / name
            with self.subTest(name=name):
                self.assertTrue(path.is_file(), msg=f"missing {name}")
                src = path.read_text(encoding="utf-8")
                lines = src.count("\n") + 1
                self.assertLessEqual(lines, MAX_LINES, msg=f"{name}={lines}")
                for sym in symbols:
                    self.assertTrue(
                        re.search(rf"\b{sym}\b", src),
                        msg=f"{name} missing {sym}",
                    )
        self.assertFalse(
            (DB / "relation-pool.ts").is_file(),
            msg="shallow relation-pool.ts barrel must stay deleted",
        )

    def test_runtime_callers_use_projection_not_builder(self):
        entry = (
            REPO / "client" / "src" / "entry-detail" / "load-entry-detail.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("projectRelationPool", entry)
        self.assertIn("relation-pool-projection", entry)
        self.assertNotIn("buildRelationPool", entry)
        # only projection module may import builder
        for path in (REPO / "client" / "src").rglob("*.ts"):
            if path.name in ("relation-pool-builder.ts", "relation-pool-projection.ts"):
                continue
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if "buildRelationPool" in text or "relation-pool-builder" in text:
                self.fail(f"runtime must not import builder: {path.relative_to(REPO)}")

    def test_builder_not_inline_ranking_tables(self):
        """SOURCE_BASE_RANK SSOT is contracts → _generated; ranking module imports it."""
        builder = (DB / "relation-pool-builder.ts").read_text(encoding="utf-8")
        ranking = (DB / "relation-pool-ranking.ts").read_text(encoding="utf-8")
        generated = (DB / "_generated" / "relation-pool-ranking.ts").read_text(
            encoding="utf-8"
        )
        self.assertIn("SOURCE_BASE_RANK", generated)
        self.assertIn("_generated/relation-pool-ranking", ranking)
        self.assertNotIn("SOURCE_BASE_RANK", builder)
        # ranking must not hand-copy the rank table
        self.assertNotIn("'project_ant': 12", ranking)
        self.assertIn("'project_ant': 12", generated)


if __name__ == "__main__":
    unittest.main()
