"""近反義模式 in_db 按需批量查詢 — behavior + no full-table scan."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from app.repositories.word_relation_repo import chars_present_in_db
from app.services.relation_ranker import RelationRanker
from app.services.relation_syntax_executor import RelationSyntaxExecutor


class CharsPresentInDbTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_returns_membership_only_for_requested_chars(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="未收錄", code="22", jyutping="", length=3),
            ])
            db.commit()

            present = chars_present_in_db(db, ["開心", "幽靈字", "快樂", ""])

            self.assertEqual(present, {"開心", "快樂"})


class RelationRankerBatchMembershipTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_in_db_flags_follow_batch_lookup_not_full_scan(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="噪音甲", code="22", jyutping="", length=3),
                Word(id=4, char="噪音乙", code="22", jyutping="", length=3),
            ])
            db.add(
                WordRelation(
                    word_id=1,
                    related_id=2,
                    relation_type="syn",
                    score=0.9,
                    source="test",
                )
            )
            db.commit()

            with patch(
                "app.repositories.word_relation_repo.load_db_char_set",
                side_effect=AssertionError("must not load full db char set"),
            ):
                pools = RelationRanker(db).rank("快樂", include_static=False, quiet=True)

            by_char = {r["char"]: r for r in pools.syns}
            self.assertTrue(by_char["開心"]["in_db"])
            self.assertEqual(by_char["開心"]["char"], "開心")

    def test_syn_mode_page_skips_full_db_char_set(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(
                    word_id=1,
                    related_id=2,
                    relation_type="syn",
                    score=0.9,
                    source="test",
                )
            )
            db.commit()

            with patch(
                "app.repositories.word_relation_repo.load_db_char_set",
                side_effect=AssertionError("syn mode must not load full db char set"),
            ) as mocked:
                page = RelationSyntaxExecutor(db).syn_mode_page(
                    "快樂", limit=160, offset=0
                )

            mocked.assert_not_called()
            self.assertEqual(page[0]["char"], "開心")
            self.assertTrue(page[0]["in_db"])


if __name__ == "__main__":
    unittest.main()
