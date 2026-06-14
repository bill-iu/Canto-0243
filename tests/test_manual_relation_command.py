"""關係補錄命令 — 重算對稱與單一交易。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from app.services.manual_relation_service import (
    ManualRelationError,
    build_expand_plan,
    create_creator_manual_relation,
    revoke_creator_manual_relation,
    validate_manual_relation_request,
)


class ManualRelationCommandTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _seed_syn_cluster_fixture(self, db):
        db.add_all([
            Word(id=1, char="快樂", code="22", jyutping="", length=2),
            Word(id=2, char="開心", code="22", jyutping="", length=2),
            Word(id=3, char="愉快", code="22", jyutping="", length=2),
        ])
        db.add(
            WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.9, source="cilin")
        )
        db.commit()

    def test_revoke_expand_matches_create_plan(self):
        Session = self._session()
        with Session() as db:
            self._seed_syn_cluster_fixture(db)
            validated = validate_manual_relation_request(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )
            plan = build_expand_plan(db, validated)

            create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )
            expanded_chars = {
                db.query(Word).filter(Word.id == rel.related_id).one().char
                for rel in db.query(WordRelation)
                .filter(WordRelation.source == "manual_syn_cluster")
                .all()
            }
            self.assertEqual(expanded_chars, set(plan))

            revoke_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )
            self.assertEqual(
                db.query(WordRelation)
                .filter(WordRelation.source.in_(("manual", "manual_syn_cluster")))
                .count(),
                0,
            )

    def test_create_rolls_back_when_expand_insert_fails(self):
        Session = self._session()
        with Session() as db:
            self._seed_syn_cluster_fixture(db)

            with patch(
                "app.services.manual_relation_service.insert_relation_candidates",
                side_effect=[(1, 0), RuntimeError("expand failed")],
            ):
                with self.assertRaises(RuntimeError):
                    create_creator_manual_relation(
                        db, seed_char="快樂", opposite_char="開心", relation_type="syn"
                    )

            self.assertEqual(
                db.query(WordRelation)
                .filter(WordRelation.source.in_(("manual", "manual_syn_cluster")))
                .count(),
                0,
            )

    def test_create_rolls_back_when_direct_duplicate_race(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.commit()

            with patch(
                "app.services.manual_relation_service.insert_relation_candidates",
                return_value=(0, 1),
            ):
                with self.assertRaises(ManualRelationError) as ctx:
                    create_creator_manual_relation(
                        db, seed_char="快樂", opposite_char="開心", relation_type="syn"
                    )
                self.assertEqual(ctx.exception.code, "already_exists")

            self.assertEqual(db.query(WordRelation).count(), 0)


if __name__ == "__main__":
    unittest.main()
