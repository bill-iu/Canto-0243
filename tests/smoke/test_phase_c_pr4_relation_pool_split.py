"""Phase C PR4: TS 近反義池 project → build → ranking (grill C4)."""
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
            # P2 #4: facade exposes projection only (not builder)
            "relation-pool.ts": ("projectRelationPool", "relationPoolPage"),
        }
        for name, symbols in expected.items():
            path = DB / name
            with self.subTest(name=name):
                self.assertTrue(path.is_file(), msg=f"missing {name}")
                src = path.read_text(encoding="utf-8")
                if name != "relation-pool.ts":
                    lines = src.count("\n") + 1
                    self.assertLessEqual(lines, MAX_LINES, msg=f"{name}={lines}")
                for sym in symbols:
                    self.assertTrue(
                        re.search(rf"\b{sym}\b", src),
                        msg=f"{name} missing {sym}",
                    )

    def test_facade_reexports_from_layers(self):
        src = (DB / "relation-pool.ts").read_text(encoding="utf-8")
        self.assertIn("relation-pool-projection", src)
        self.assertNotIn("relation-pool-builder", src)
        self.assertNotIn("buildRelationPool", src)
        # facade should stay thin
        self.assertLess(src.count("\n") + 1, 80)

    def test_runtime_callers_use_projection_not_builder(self):
        entry = (
            REPO / "client" / "src" / "entry-detail" / "load-entry-detail.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("projectRelationPool", entry)
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
        """Ranking SOURCE_BASE_RANK lives in ranking module, not builder."""
        builder = (DB / "relation-pool-builder.ts").read_text(encoding="utf-8")
        ranking = (DB / "relation-pool-ranking.ts").read_text(encoding="utf-8")
        self.assertIn("SOURCE_BASE_RANK", ranking)
        self.assertNotIn("SOURCE_BASE_RANK", builder)


if __name__ == "__main__":
    unittest.main()
