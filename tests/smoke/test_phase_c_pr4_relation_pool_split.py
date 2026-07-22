"""Phase C PR4 / C7: TS 近反義池 deep package; shims retired (P3#3)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "client" / "src" / "db"
POOL = DB / "relation-pool"
MAX_LINES = 350
SHIM_TS = (
    "relation-pool-ranking.ts",
    "relation-pool-builder.ts",
    "relation-pool-projection.ts",
    "relation-pool-snapshot.ts",
)
SHIM_PY = ("pool.py", "pool_builder.py", "pool_projection.py", "ranking.py")


class PhaseCPr4RelationPoolSplit(unittest.TestCase):
    def test_module_layout(self):
        expected = {
            "ranking.ts": ("finalScore", "mergeRelationPools", "sortSynPool", "sortAntPool"),
            "builder.ts": ("buildRelationPool", "fetchDbRelations"),
            "projection.ts": ("projectRelationPool", "relationPoolPage"),
        }
        for name, symbols in expected.items():
            path = POOL / name
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
        self.assertTrue((POOL / "index.ts").is_file())
        self.assertFalse(
            (DB / "relation-pool.ts").is_file(),
            msg="shallow relation-pool.ts barrel must stay deleted",
        )
        for shim in SHIM_TS:
            self.assertFalse(
                (DB / shim).is_file(),
                msg=f"shim must be deleted: {shim}",
            )
        self.assertFalse(
            (DB / "_generated" / "relation-pool-ranking.ts").is_file(),
            msg="db/_generated relation-pool-ranking shim must be deleted",
        )

    def test_runtime_callers_use_projection_not_builder(self):
        entry = (
            REPO / "client" / "src" / "entry-detail" / "load-entry-detail.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("projectRelationPool", entry)
        self.assertIn("relation-pool", entry)
        self.assertNotIn("buildRelationPool", entry)
        for path in (REPO / "client" / "src").rglob("*.ts"):
            if path.parent == POOL and path.name in ("builder.ts", "projection.ts"):
                continue
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if (
                "buildRelationPool" in text
                or "relation-pool/builder" in text
                or "relation-pool-builder" in text
            ):
                self.fail(f"runtime must not import builder: {path.relative_to(REPO)}")
            # Ban legacy root shims only (not relation-pool/_generated/relation-pool-ranking.ts)
            if re.search(
                r"""from ['"]\.\.?/(?:\.\./)*relation-pool-(projection|builder|snapshot|ranking)""",
                text,
            ) or re.search(
                r"""from ['"].*src/db/relation-pool-(projection|builder|snapshot|ranking)""",
                text,
            ):
                self.fail(f"runtime must not import pool shim path: {path.relative_to(REPO)}")

    def test_builder_not_inline_ranking_tables(self):
        builder = (POOL / "builder.ts").read_text(encoding="utf-8")
        ranking = (POOL / "ranking.ts").read_text(encoding="utf-8")
        generated = (POOL / "_generated" / "relation-pool-ranking.ts").read_text(
            encoding="utf-8"
        )
        self.assertIn("SOURCE_BASE_RANK", generated)
        self.assertIn("_generated/relation-pool-ranking", ranking)
        self.assertNotIn("SOURCE_BASE_RANK", builder)
        self.assertNotIn("'project_ant': 12", ranking)
        self.assertIn("'project_ant': 12", generated)

    def test_python_package_layout(self):
        root = REPO / "app" / "domain" / "relation_pool"
        self.assertTrue((root / "__init__.py").is_file())
        init = (root / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("project_relation_pool", init)
        self.assertNotIn("build_pool", init)
        self.assertIn("__getattr__", init)
        for name in ("pool_projection.py", "pool_builder.py", "pool.py", "ranking.py"):
            self.assertTrue((root / name).is_file(), msg=name)
        rel = REPO / "app" / "domain" / "relations"
        for name in SHIM_PY:
            self.assertFalse(
                (rel / name).is_file(),
                msg=f"Python pool shim must be deleted: relations/{name}",
            )
        for path in (REPO / "app").rglob("*.py"):
            if "relation_pool" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if "domain.relations.pool" in text or "domain.relations.ranking" in text:
                self.fail(f"must not import pool shim package: {path.relative_to(REPO)}")


if __name__ == "__main__":
    unittest.main()
