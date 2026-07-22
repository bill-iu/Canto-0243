"""C4: build-db --stage resolution + help paths."""
from __future__ import annotations

import argparse
import unittest

from ingest.cli import BUILD_DB_PATH_HINT, resolve_build_db_stage


class BuildDbStageTests(unittest.TestCase):
    def test_default_all(self) -> None:
        ns = argparse.Namespace(stage="all", skip_relations=False)
        self.assertEqual(resolve_build_db_stage(ns), "all")

    def test_skip_relations_aliases_words(self) -> None:
        ns = argparse.Namespace(stage="all", skip_relations=True)
        self.assertEqual(resolve_build_db_stage(ns), "words")

    def test_skip_relations_conflicts_with_relations_stage(self) -> None:
        ns = argparse.Namespace(stage="relations", skip_relations=True)
        with self.assertRaises(ValueError):
            resolve_build_db_stage(ns)

    def test_hint_lists_stages(self) -> None:
        self.assertIn("--stage words", BUILD_DB_PATH_HINT)
        self.assertIn("--stage relations", BUILD_DB_PATH_HINT)
        self.assertIn("--stage seal", BUILD_DB_PATH_HINT)
        self.assertIn("apply-manual-relations", BUILD_DB_PATH_HINT)


if __name__ == "__main__":
    unittest.main()
