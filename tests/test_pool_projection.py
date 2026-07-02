"""pool_projection 與 build_pool 行為等價（runtime 讀取收口）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.pool import build_pool
from app.domain.relations.pool_projection import (
    project_relation_pool,
    relation_pool_chars,
    relation_pool_page,
)
from app.models.word import Word, WordRelation


class PoolProjectionEquivalenceTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_project_relation_pool_matches_build_pool_quiet(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="開心", code="33", jyutping="hoi1 sam1", length=2),
            ])
            db.add(
                WordRelation(
                    word_id=1, related_id=2, relation_type="syn", score=0.9, source="cilin"
                )
            )
            db.commit()

            legacy = build_pool(db, "快樂", include_static=False, quiet=True)
            projected = project_relation_pool(db, "快樂", include_static=False)

            self.assertEqual(projected.query, legacy.query)
            self.assertEqual(projected.syns, legacy.syns)
            self.assertEqual(projected.ants, legacy.ants)
            self.assertEqual(projected.semantic, legacy.semantic)

    def test_relation_pool_page_and_chars_delegate_to_snapshot(self):
        Session = self._session()
        with Session() as db:
            db.add(Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2))
            db.commit()

            snapshot = project_relation_pool(db, "快樂", include_static=False)
            self.assertEqual(
                relation_pool_page(db, "快樂", limit=5, offset=0, include_static=False),
                snapshot.page(5, 0),
            )
            self.assertEqual(
                relation_pool_chars(
                    db, "快樂", "syn", include_static=False
                ),
                snapshot.chars("syn"),
            )

    def test_include_derived_ant_false_omits_runtime_derived(self):
        from unittest.mock import MagicMock

        from app.domain.relations.cilin_derived import CILIN_DERIVED_SOURCE
        from app.domain.relations.mirror_ant import MIRROR_SOURCE

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

            full = build_pool(
                db,
                "快樂",
                include_static=True,
                thesaurus=thesaurus,
                membership=membership,
                quiet=True,
            )
            direct = build_pool(
                db,
                "快樂",
                include_static=True,
                thesaurus=thesaurus,
                membership=membership,
                include_derived_ant=False,
                quiet=True,
            )
            full_sources = {r["char"]: r.get("source") for r in full.ants}
            direct_chars = [r["char"] for r in direct.ants]

            self.assertEqual(full_sources.get("傷心"), CILIN_DERIVED_SOURCE)
            self.assertEqual(full_sources.get("哀愁"), MIRROR_SOURCE)
            self.assertIn("悲傷", direct_chars)
            self.assertNotIn("傷心", direct_chars)
            self.assertNotIn("哀愁", direct_chars)

            via_projection = relation_pool_chars(
                db,
                "快樂",
                "ant",
                include_static=True,
                thesaurus=thesaurus,
                membership=membership,
                include_derived_ant=False,
                allow_inject=False,
            )
            self.assertEqual(via_projection, direct_chars)


if __name__ == "__main__":
    unittest.main()
