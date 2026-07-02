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


if __name__ == "__main__":
    unittest.main()
