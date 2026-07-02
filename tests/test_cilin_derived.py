"""詞林衍生反義核心 — per-head 字面對（CONTEXT § 詞林衍生反義）。"""

import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.cilin_derived import (
    CILIN_DERIVED_CONFIDENCE,
    cilin_derived_ant_pairs,
    collect_lexicon_cilin_derived_pairs,
    direct_ant_seeds_for_head,
)
from app.models.word import Word, WordRelation


class CilinDerivedCoreTests(unittest.TestCase):
    def test_cilin_derived_ant_pairs_golden(self):
        pairs = cilin_derived_ant_pairs(
            "快樂",
            ["悲傷"],
            cilin_synonyms_of=lambda w: {"悲傷": ["傷心", "難過"]}.get(w, []),
            membership={"快樂", "悲傷", "傷心", "難過"},
        )
        self.assertEqual(set(pairs), {("快樂", "傷心"), ("快樂", "難過")})

    def test_cilin_derived_skips_outside_membership_and_self(self):
        pairs = cilin_derived_ant_pairs(
            "快樂",
            ["悲傷"],
            cilin_synonyms_of=lambda w: ["傷心", "快樂", "未收錄"],
            membership={"快樂", "悲傷", "傷心"},
        )
        self.assertEqual(pairs, [("快樂", "傷心")])

    def test_direct_ant_seeds_db_and_static(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        thesaurus = MagicMock()
        thesaurus.get_antonyms.side_effect = lambda q: {"快樂": ["痛苦"]}.get(q, [])
        thesaurus.get_cilin_synonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="痛苦", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong")
            )
            db.add(
                WordRelation(
                    word_id=1,
                    related_id=3,
                    relation_type="ant",
                    source="ant_cilin_exanded",
                )
            )
            db.commit()
            membership = {"快樂", "悲傷", "痛苦"}
            seeds = direct_ant_seeds_for_head(
                db, "快樂", thesaurus=thesaurus, membership=membership, include_static=True
            )
            self.assertEqual(set(seeds), {"悲傷", "痛苦"})

    def test_collect_lexicon_pairs_matches_per_head_core(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        thesaurus = MagicMock()
        thesaurus.get_cilin_synonyms.side_effect = lambda w: {
            "悲傷": ["傷心", "難過"],
        }.get(w, [])
        thesaurus.get_antonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
                Word(id=4, char="難過", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong")
            )
            db.commit()
            membership = {"快樂", "悲傷", "傷心", "難過"}
            pairs = collect_lexicon_cilin_derived_pairs(
                db, thesaurus, membership=membership, include_static=False
            )
            self.assertEqual(set(pairs), {("快樂", "傷心"), ("快樂", "難過")})


if __name__ == "__main__":
    unittest.main()
