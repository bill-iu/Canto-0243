"""CharRelationGraph — 直接近義鄰居與 ! 鏡射對（候選 #2）."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.graph import CharRelationGraph
from app.models.word import Word, WordRelation


class FakeThesaurus:
    def ensure_loaded(self) -> None:
        return None

    def get_synonyms(self, query: str) -> list[str]:
        if query == "香":
            return ["芬芳"]
        return []

    def get_antonyms(self, query: str) -> list[str]:
        return []

    def iter_antonym_edges(self):
        return iter([])


class CharRelationGraphTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_direct_syn_neighbors_from_db_bidirectional(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=2, char="悲傷", code="33", jyutping="", length=2),
                Word(id=3, char="傷心", code="33", jyutping="", length=2),
                Word(id=4, char="難過", code="33", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=2, related_id=3, relation_type="syn", source="cilin"),
                WordRelation(word_id=2, related_id=4, relation_type="syn", source="cilin"),
            ])
            db.commit()

            graph = CharRelationGraph(db, FakeThesaurus(), membership={"悲傷", "傷心", "難過"})
            neighbors = graph.direct_syn_neighbors("悲傷")

            self.assertEqual(neighbors, {"傷心", "難過"})

    def test_direct_syn_neighbors_include_static_thesaurus_port(self):
        Session = self._session()
        with Session() as db:
            db.add(Word(id=1, char="香", code="1", jyutping="", length=1))
            db.commit()

            graph = CharRelationGraph(db, FakeThesaurus(), membership={"香", "芬芳"})
            neighbors = graph.direct_syn_neighbors("香")

            self.assertIn("芬芳", neighbors)

    def test_mirror_ant_pairs_match_runtime_expand_pattern(self):
        Session = self._session()
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
            graph = CharRelationGraph(db, FakeThesaurus(), membership=membership)
            pairs = graph.collect_mirror_ant_pairs(include_static=False)

            self.assertIn(("開心", "悲傷"), pairs)
            self.assertIn(("開心", "傷心"), pairs)
            self.assertIn(("開心", "難過"), pairs)


if __name__ == "__main__":
    unittest.main()
