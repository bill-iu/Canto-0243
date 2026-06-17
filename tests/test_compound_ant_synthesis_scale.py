"""反義複合合成：唔應對每字重掃 ant pair DB。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_ant import (
    build_compound_ant_snapshot,
    reset_compound_ant_snapshot_for_tests,
    search_compound_ant,
    synthesize_compound_ant_literals,
)
from app.domain.relations.graph import CharRelationGraph, default_char_relation_graph
from app.models.word import Word, WordRelation


class CompoundAntSynthesisScaleTests(unittest.TestCase):
    def setUp(self):
        reset_compound_ant_snapshot_for_tests()

    def tearDown(self):
        reset_compound_ant_snapshot_for_tests()

    def _session_with_many_chars(self, n: int = 40):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        words = []
        relations = []
        for i in range(n):
            a = chr(0x4E00 + i)
            b = chr(0x4E00 + ((i + 1) % n))
            words.append(Word(id=i * 2 + 1, char=a, code="3", jyutping="aa1", length=1))
            words.append(Word(id=i * 2 + 2, char=b, code="3", jyutping="bb1", length=1))
            words.append(
                Word(id=1000 + i, char=a + b, code="33", jyutping="aa1 bb1", length=2)
            )
            relations.append(
                WordRelation(
                    word_id=i * 2 + 1,
                    related_id=i * 2 + 2,
                    relation_type="ant",
                    source="test",
                )
            )
        session.add_all(words)
        session.add_all(relations)
        session.commit()
        return session

    def test_synthesize_scans_ant_pairs_once_not_per_char(self):
        session = self._session_with_many_chars(40)
        try:
            snapshot = build_compound_ant_snapshot(session)
            graph = default_char_relation_graph(session)
            with patch.object(
                CharRelationGraph,
                "_direct_ant_oriented_pairs",
                wraps=graph._direct_ant_oriented_pairs,
            ) as spy:
                synthesize_compound_ant_literals(snapshot, graph, k=12)
            self.assertLessEqual(
                spy.call_count,
                2,
                "ant pair DB scan should be cached, not once per single char",
            )
        finally:
            session.close()

    def test_search_compound_ant_first_call_returns_promptly(self):
        import time

        session = self._session_with_many_chars(60)
        try:
            t0 = time.perf_counter()
            tiers = search_compound_ant(session, k=12)
            elapsed = time.perf_counter() - t0
            self.assertGreater(len(tiers), 0)
            self.assertLess(elapsed, 2.0, f"!! tier build took {elapsed:.2f}s")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
