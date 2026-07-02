"""黃金查詢集 CI 子集 — parse + dispatch journey on fixture / seeded DB."""
from __future__ import annotations

import unittest

from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_parse import RelationLookupQuery, normalize_and_parse

from tests.smoke.golden_queries import GOLDEN_QUERY_JOURNEYS
from tests.smoke.helpers import fixture_sessionmaker, memory_sessionmaker, seed_happy_sad


class QueryJourneySmokeTests(unittest.TestCase):
    def _seed_memory(self, db, seed: str) -> None:
        if seed == "left_code":
            db.add_all([
                Word(
                    char="好我",
                    code="34",
                    jyutping="hou2 ngo5",
                    finals='["ou", "o"]',
                    initials='["h", "ng"]',
                    length=2,
                ),
                Word(
                    char="小馬騮",
                    code="944",
                    jyutping="siu2 maa5 ngau4",
                    finals='["iu", "aa", "au"]',
                    initials='["s", "m", "ng"]',
                    length=3,
                ),
            ])
            db.commit()
        elif seed == "relation_syn":
            seed_happy_sad(db)
        else:
            raise ValueError(seed)

    def test_golden_query_journeys(self):
        for case in GOLDEN_QUERY_JOURNEYS:
            with self.subTest(q=case.query, mode=case.mode, db=case.db):
                parsed = normalize_and_parse(case.query)
                self.assertIsNotNone(parsed)
                if case.mode == "syn" and case.seed == "relation_syn":
                    self.assertIsInstance(parsed, RelationLookupQuery)
                    self.assertEqual(parsed.relation_kind, "syn")

                if case.db == "fixture":
                    Session = fixture_sessionmaker()
                else:
                    Session = memory_sessionmaker()

                with Session() as db:
                    if case.db == "memory" and case.seed:
                        self._seed_memory(db, case.seed)
                    results = search_words(
                        q=case.query,
                        mode=case.mode,
                        db=db,
                        limit=10,
                        offset=0,
                    )
                words = [r["char"] for r in results if r.get("result_type") == "word"]
                self.assertGreaterEqual(len(words), case.min_words)
                for char in case.must_include:
                    self.assertIn(char, words)


if __name__ == "__main__":
    unittest.main()
