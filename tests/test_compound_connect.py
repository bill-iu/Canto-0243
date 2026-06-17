"""填詞連接詞複合（!與!／~與~）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_ant import reset_compound_ant_snapshot_for_tests
from app.domain.relations.compound_syn import reset_compound_syn_snapshot_for_tests
from app.models.word import Word, WordRelation
from app.services.query_dispatch import search_words
from app.services.query_parse import CompoundConnectAntQuery, CompoundConnectSynQuery, parse_query


class CompoundConnectTests(unittest.TestCase):
    def setUp(self):
        reset_compound_ant_snapshot_for_tests()
        reset_compound_syn_snapshot_for_tests()

    def tearDown(self):
        reset_compound_ant_snapshot_for_tests()
        reset_compound_syn_snapshot_for_tests()

    def test_parse_connective_ant_and_syn(self):
        ant = parse_query("!與!")
        self.assertIsInstance(ant, CompoundConnectAntQuery)
        self.assertEqual(ant.connective, "與")
        syn = parse_query("349~與~你")
        self.assertIsInstance(syn, CompoundConnectSynQuery)
        self.assertEqual(syn.code_prefix, "349")
        self.assertEqual(syn.connective, "與")
        self.assertEqual(syn.rhyme_char, "你")

    def test_connective_ant_search(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as session:
            session.add_all([
                Word(id=1, char="生", code="3", jyutping="saang1", length=1),
                Word(id=2, char="死", code="3", jyutping="sei2", length=1),
                Word(id=10, char="生死", code="33", jyutping="saang1 sei2", length=2),
                Word(id=11, char="生與死", code="333", jyutping="saang1 jyu5 sei2", length=3),
            ])
            session.add(
                WordRelation(word_id=1, related_id=2, relation_type="ant", source="test")
            )
            session.commit()

            results = search_words(q="!與!", mode="m1", db=session, limit=20, offset=0)
            chars = [r["char"] for r in results]
            self.assertIn("生與死", chars)


if __name__ == "__main__":
    unittest.main()
