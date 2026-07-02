"""近反義池 journey — build_pool、投影、bridge、衍生層。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.domain.relations.pool import build_pool
from app.domain.relations.pool_projection import (
    project_relation_pool,
    relation_pool_chars,
)
from app.models.word import Word, WordRelation
from ingest.bridge_pool_context import IngestBridgePoolContext

from tests.smoke.helpers import memory_sessionmaker, seed_happy_sad


class RelationJourneySmokeTests(unittest.TestCase):
    def test_build_pool_syn_chars_and_projection_equivalence(self):
        Session = memory_sessionmaker()
        with Session() as db:
            seed_happy_sad(db)
            legacy = build_pool(db, "快樂", include_static=False, quiet=True)
            projected = project_relation_pool(db, "快樂", include_static=False)
            self.assertEqual(projected.syns, legacy.syns)
            self.assertEqual(
                relation_pool_chars(db, "快樂", "syn", include_static=False),
                ["開心", "愉快"],
            )

    def test_runtime_cilin_and_mirror_derived_ants(self):
        Session = memory_sessionmaker()
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.side_effect = lambda w: {
            "悲傷": ["傷心", "難過"],
        }.get(w, [])
        thesaurus.get_synonyms.side_effect = lambda w: {
            "悲傷": ["傷心", "哀愁"],
        }.get(w, [])
        thesaurus.get_antonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
                Word(id=4, char="難過", code="22", jyutping="", length=2),
                Word(id=5, char="哀愁", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong")
            )
            db.commit()
            membership = {"快樂", "悲傷", "傷心", "難過", "哀愁"}
            snapshot = build_pool(
                db,
                "快樂",
                include_static=True,
                thesaurus=thesaurus,
                membership=membership,
                quiet=True,
            )
            by_source = {r["char"]: r.get("source") for r in snapshot.ants}
            self.assertEqual(by_source.get("傷心"), "ant_cilin_exanded")
            self.assertEqual(by_source.get("哀愁"), "ant_syn_mirror")

    def test_ignores_stale_db_derived_ant_rows(self):
        Session = memory_sessionmaker()
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.return_value = []
        thesaurus.get_synonyms.return_value = []
        thesaurus.get_antonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="過期字", code="22", jyutping="", length=3),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong"))
            db.add(
                WordRelation(
                    word_id=1,
                    related_id=3,
                    relation_type="ant",
                    source="ant_cilin_exanded",
                )
            )
            db.commit()
            membership = {"快樂", "悲傷", "過期字"}
            snapshot = build_pool(
                db,
                "快樂",
                include_static=False,
                thesaurus=thesaurus,
                membership=membership,
                quiet=True,
            )
            ant_chars = [r["char"] for r in snapshot.ants]
            self.assertIn("悲傷", ant_chars)
            self.assertNotIn("過期字", ant_chars)

    def test_ant_syn_bridge_rows_in_db_fetch(self):
        Session = memory_sessionmaker()
        with Session() as db:
            seed_happy_sad(db)
            snapshot = build_pool(db, "開心", include_static=False, quiet=True)
            ant_chars = [r["char"] for r in snapshot.ants]
            self.assertIn("悲傷", ant_chars)
            self.assertIn("傷心", ant_chars)

    def test_include_derived_ant_false_omits_runtime_derived(self):
        Session = memory_sessionmaker()
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.side_effect = lambda w: {"悲傷": ["傷心"]}.get(w, [])
        thesaurus.get_synonyms.side_effect = lambda w: {"悲傷": ["傷心", "哀愁"]}.get(w, [])
        thesaurus.get_antonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
                Word(id=4, char="哀愁", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong"))
            db.commit()
            membership = {"快樂", "悲傷", "傷心", "哀愁"}
            direct = relation_pool_chars(
                db,
                "快樂",
                "ant",
                include_static=True,
                thesaurus=thesaurus,
                membership=membership,
                include_derived_ant=False,
                allow_inject=False,
            )
            self.assertIn("悲傷", direct)
            self.assertNotIn("傷心", direct)
            self.assertNotIn("哀愁", direct)

    def test_ingest_bridge_pool_matches_projection_without_derived(self):
        Session = memory_sessionmaker()
        with Session() as db:
            seed_happy_sad(db)
            pool_ctx = IngestBridgePoolContext(db, include_static=False)
            for kind in ("syn", "ant"):
                via_projection = relation_pool_chars(
                    db,
                    "快樂",
                    kind,
                    allow_inject=False,
                    include_static=False,
                    thesaurus=pool_ctx.thesaurus,
                    membership=pool_ctx._membership,
                    include_derived_ant=False,
                )
                self.assertEqual(pool_ctx.relation_chars("快樂", kind), via_projection)


if __name__ == "__main__":
    unittest.main()
