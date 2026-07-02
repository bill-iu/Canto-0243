"""反義端點鏡射核心 — per-head 字面對（CONTEXT § 反義端點鏡射）。"""

import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.cilin_derived import direct_ant_seeds_for_head
from app.domain.relations.graph import CharRelationGraph
from app.domain.relations.mirror_ant import (
    MIRROR_CONFIDENCE,
    collect_lexicon_mirror_pairs,
    mirror_ant_pairs,
)
from app.models.word import Word, WordRelation


class MirrorAntCoreTests(unittest.TestCase):
    def test_mirror_ant_pairs_golden(self):
        pairs = mirror_ant_pairs(
            "開心",
            ["悲傷"],
            syn_neighbors_of=lambda w: {
                "悲傷": ["傷心", "難過"],
            }.get(w, []),
            membership={"開心", "悲傷", "傷心", "難過"},
        )
        self.assertEqual(set(pairs), {("開心", "傷心"), ("開心", "難過")})

    def test_collect_lexicon_mirror_pairs_per_head(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        thesaurus = MagicMock()
        thesaurus.get_synonyms.side_effect = lambda w: {
            "悲傷": ["傷心", "難過"],
        }.get(w, [])
        thesaurus.get_antonyms.return_value = []
        thesaurus.get_cilin_synonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="開心", code="33", jyutping="", length=2),
                Word(id=2, char="悲傷", code="33", jyutping="", length=2),
                Word(id=3, char="傷心", code="33", jyutping="", length=2),
                Word(id=4, char="難過", code="33", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="test"))
            db.add_all([
                WordRelation(word_id=2, related_id=3, relation_type="syn", source="cilin"),
                WordRelation(word_id=2, related_id=4, relation_type="syn", source="cilin"),
            ])
            db.commit()
            membership = {"開心", "悲傷", "傷心", "難過"}
            graph = CharRelationGraph(db, thesaurus, membership=membership)
            pairs = collect_lexicon_mirror_pairs(
                db,
                thesaurus,
                membership=membership,
                include_static=False,
                graph=graph,
            )
            self.assertEqual(set(pairs), {("開心", "傷心"), ("開心", "難過")})


if __name__ == "__main__":
    unittest.main()
