"""Architecture boundary invariants kept in unittest smoke (see scripts/check_seams.py)."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_runtime_services_do_not_import_build_pool(self):
        """app/services runtime uses 近反義池投影 only (relation_pool package after P3#3)."""
        services = REPO_ROOT / "app" / "services"
        for path in services.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertNotIn("build_pool", source)
                if "project_relation_pool" in source:
                    self.assertIn("relation_pool", source)
                    self.assertNotIn("domain.relations.pool", source)

    def test_ingest_bridge_pool_context_uses_projection(self):
        path = REPO_ROOT / "ingest" / "bridge_pool_context.py"
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("build_pool", source)
        self.assertIn("project_relation_pool", source)
        self.assertIn("relation_pool", source)

    def test_entry_detail_uses_projection(self):
        path = REPO_ROOT / "app" / "services" / "entry_detail.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("project_relation_pool", source)
        self.assertNotIn("build_pool", source)

    def test_reference_reading_does_not_import_services(self):
        path = REPO_ROOT / "app" / "domain" / "lexicon" / "reference_reading.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertFalse(node.module.startswith("app.services"))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(alias.name.startswith("app.services"))


if __name__ == "__main__":
    unittest.main()
