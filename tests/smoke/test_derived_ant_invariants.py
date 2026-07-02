"""詞林衍生反義 + 反義端點鏡射 per-head 核心 invariant。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.domain.relations.cilin_derived import (
    cilin_derived_ant_pairs,
    collect_lexicon_cilin_derived_pairs,
    direct_ant_seeds_for_head,
)
from app.domain.relations.graph import CharRelationGraph
from app.domain.relations.mirror_ant import collect_lexicon_mirror_pairs, mirror_ant_pairs
from app.models.word import Word, WordRelation

from tests.smoke.helpers import memory_sessionmaker


class DerivedAntInvariantTests(unittest.TestCase):
    def test_cilin_derived_ant_pairs_golden(self):
        pairs = cilin_derived_ant_pairs(
            "快樂",
            ["悲傷"],
            cilin_synonyms_of=lambda w: {"悲傷": ["傷心", "難過"]}.get(w, []),
            membership={"快樂", "悲傷", "傷心", "難過"},
        )
        self.assertEqual(set(pairs), {("快樂", "傷心"), ("快樂", "難過")})

    def test_mirror_ant_pairs_golden(self):
        pairs = mirror_ant_pairs(
            "開心",
            ["悲傷"],
            syn_neighbors_of=lambda w: {"悲傷": ["傷心", "難過"]}.get(w, []),
            membership={"開心", "悲傷", "傷心", "難過"},
        )
        self.assertEqual(set(pairs), {("開心", "傷心"), ("開心", "難過")})

    def test_direct_ant_seeds_excludes_db_derived_source(self):
        Session = memory_sessionmaker()
        thesaurus = MagicMock()
        thesaurus.get_antonyms.side_effect = lambda q: {"快樂": ["痛苦"]}.get(q, [])
        thesaurus.get_cilin_synonyms.return_value = []

        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="痛苦", code="22", jyutping="", length=2),
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
            seeds = direct_ant_seeds_for_head(
                db,
                "快樂",
                thesaurus=thesaurus,
                membership={"快樂", "悲傷", "痛苦"},
                include_static=True,
            )
            self.assertEqual(set(seeds), {"悲傷", "痛苦"})

    def test_collect_lexicon_cilin_derived_pairs(self):
        Session = memory_sessionmaker()
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
            db.add(WordRelation(word_id=1, related_id=2, relation_type="ant", source="guotong"))
            db.commit()
            membership = {"快樂", "悲傷", "傷心", "難過"}
            pairs = collect_lexicon_cilin_derived_pairs(
                db, thesaurus, membership=membership, include_static=False
            )
            self.assertEqual(set(pairs), {("快樂", "傷心"), ("快樂", "難過")})

    def test_collect_lexicon_mirror_pairs_per_head(self):
        Session = memory_sessionmaker()
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
