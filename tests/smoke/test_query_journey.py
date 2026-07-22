"""黃金查詢集 CI 子集 — parse + dispatch journey on fixture / seeded DB."""
from __future__ import annotations

import unittest

from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_parse import RelationLookupQuery, is_relation_syntax_query, normalize_and_parse

from tests.smoke.golden_queries import GOLDEN_QUERY_JOURNEYS
from tests.smoke.helpers import (
    LYRICS_DB,
    fixture_sessionmaker,
    lyrics_sessionmaker,
    memory_sessionmaker,
    seed_happy_sad,
)


class QueryJourneySmokeTests(unittest.TestCase):
    def _seed_memory(self, db, seed: str) -> None:
        if seed == "left_code":
            # ADR-0037: runtime only accepts j2 compact phoneme fields
            from app.domain.lexicon.phoneme_codec import encode_phoneme_list

            db.add_all([
                Word(
                    char="好我",
                    code="34",
                    jyutping="hou2 ngo5",
                    finals=encode_phoneme_list(["ou", "o"], "final"),
                    initials=encode_phoneme_list(["h", "ng"], "initial"),
                    length=2,
                ),
                Word(
                    char="小馬騮",
                    code="944",
                    jyutping="siu2 maa5 ngau4",
                    finals=encode_phoneme_list(["iu", "aa", "au"], "final"),
                    initials=encode_phoneme_list(["s", "m", "ng"], "initial"),
                    length=3,
                ),
            ])
            db.commit()
        elif seed == "relation_syn":
            seed_happy_sad(db)
        else:
            raise ValueError(seed)

    def _run_journey_case(self, case) -> None:
        parsed = normalize_and_parse(case.query)
        self.assertIsNotNone(parsed)
        if case.mode == "syn" and case.seed == "relation_syn" and is_relation_syntax_query(case.query):
            self.assertIsInstance(parsed, RelationLookupQuery)
            if case.query.startswith("~"):
                self.assertEqual(parsed.relation_kind, "syn")

        if case.db == "fixture":
            Session = fixture_sessionmaker()
        elif case.db == "lyrics":
            Session = lyrics_sessionmaker()
        else:
            Session = memory_sessionmaker()

        limit = 500 if case.must_include else 10
        with Session() as db:
            if case.db == "memory" and case.seed:
                self._seed_memory(db, case.seed)
            results = search_words(
                q=case.query,
                mode=case.mode,
                db=db,
                limit=limit,
                offset=0,
            )
        if case.mode == "syn":
            words = [r["char"] for r in results if r.get("char")]
        else:
            words = [r["char"] for r in results if r.get("result_type") == "word"]
        self.assertGreaterEqual(len(words), case.min_words)
        for char in case.must_include:
            self.assertIn(char, words)

    def test_golden_query_journeys(self):
        for case in GOLDEN_QUERY_JOURNEYS:
            if case.db == "lyrics":
                continue
            with self.subTest(q=case.query, mode=case.mode, db=case.db):
                self._run_journey_case(case)

    @unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
    def test_lyrics_golden_query_journeys(self):
        for case in GOLDEN_QUERY_JOURNEYS:
            if case.db != "lyrics":
                continue
            with self.subTest(q=case.query, mode=case.mode, db=case.db):
                self._run_journey_case(case)


if __name__ == "__main__":
    unittest.main()
