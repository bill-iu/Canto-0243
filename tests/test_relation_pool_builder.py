"""近反義池 — build_pool + PoolSnapshot."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.pool import build_pool
from app.models.word import Word, WordRelation


class RelationPoolTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _seed_happy_sad(self, db):
        db.add_all([
            Word(id=1, char="快樂", code="22", jyutping="", length=2),
            Word(id=2, char="開心", code="22", jyutping="", length=2),
            Word(id=3, char="愉快", code="22", jyutping="", length=2),
            Word(id=4, char="悲傷", code="22", jyutping="", length=2),
        ])
        db.add_all([
            WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.95, source="cilin"),
            WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.80, source="test"),
            WordRelation(word_id=2, related_id=4, relation_type="ant", score=0.90, source="antisem"),
        ])
        db.commit()

    def test_build_pool_syn_and_ant_chars(self):
        Session = self._session()
        with Session() as db:
            self._seed_happy_sad(db)
            snapshot = build_pool(db, "快樂", include_static=False, quiet=True)

            self.assertEqual(snapshot.chars("syn"), ["開心", "愉快"])
            self.assertEqual(snapshot.chars("ant"), [])

    def test_runtime_cilin_derived_ant_without_db_derived_rows(self):
        from unittest.mock import MagicMock

        Session = self._session()
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.side_effect = lambda w: {
            "悲傷": ["傷心", "難過"],
        }.get(w, [])
        thesaurus.get_synonyms.return_value = []
        thesaurus.get_antonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
                Word(id=4, char="難過", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(
                    word_id=1, related_id=2, relation_type="ant", score=0.9, source="guotong"
                )
            )
            db.commit()

            membership = {"快樂", "悲傷", "傷心", "難過"}
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
            self.assertIn("傷心", ant_chars)
            self.assertIn("難過", ant_chars)
            derived = [r for r in snapshot.ants if r.get("source") == "ant_cilin_exanded"]
            self.assertEqual({r["char"] for r in derived}, {"傷心", "難過"})

    def test_ignores_stale_db_derived_ant_rows(self):
        from unittest.mock import MagicMock

        Session = self._session()
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

    def test_runtime_mirror_ant_from_full_syn_neighbors(self):
        from unittest.mock import MagicMock

        Session = self._session()
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.side_effect = lambda w: {
            "悲傷": ["傷心"],
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
                Word(id=4, char="哀愁", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong"))
            db.commit()

            membership = {"快樂", "悲傷", "傷心", "哀愁"}
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

    def test_process_cached_graph_reused_across_build_pool_calls(self):
        from unittest.mock import MagicMock, patch

        from app.domain.relations.graph import clear_process_cached_graph

        clear_process_cached_graph()
        Session = self._session()
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.return_value = []
        thesaurus.get_synonyms.return_value = []
        thesaurus.get_antonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong"))
            db.commit()
            membership = {"快樂", "悲傷"}

            with patch(
                "app.domain.relations.graph.CharRelationGraph",
                wraps=__import__(
                    "app.domain.relations.graph", fromlist=["CharRelationGraph"]
                ).CharRelationGraph,
            ) as graph_cls:
                build_pool(
                    db, "快樂", include_static=False, thesaurus=thesaurus,
                    membership=membership, quiet=True,
                )
                build_pool(
                    db, "悲傷", include_static=False, thesaurus=thesaurus,
                    membership=membership, quiet=True,
                )
                self.assertEqual(graph_cls.call_count, 1)
        clear_process_cached_graph()

    def test_ingest_cached_membership_skips_full_table_scan_per_query(self):
        Session = self._session()
        with Session() as db:
            self._seed_happy_sad(db)
            membership = {"快樂", "開心", "愉快", "悲傷"}

            with patch(
                "app.domain.relations.pool_builder.chars_present_in_db",
                side_effect=AssertionError("ingest must use cached membership"),
            ):
                snapshot = build_pool(
                    db, "快樂", include_static=False, membership=membership, quiet=True
                )

            self.assertEqual(snapshot.chars("syn"), ["開心", "愉快"])


if __name__ == "__main__":
    unittest.main()
