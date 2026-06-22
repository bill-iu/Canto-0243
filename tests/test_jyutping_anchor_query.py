"""粵拼錨與三格韻錨查詢 — 行為測試（CONTEXT § 粵拼錨、三格韻錨查詢）。"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_parse import JyutpingAnchorQuery, parse_query
from app.services.query_lexer import normalize_search_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class TripleRhymeAnchorSearchTests(unittest.TestCase):
    def test_middle_rhyme_anchor_finds_hong_kong_person(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="港",
                        code="3",
                        jyutping="gong2",
                        finals='["ong"]',
                        initials='["g"]',
                        length=1,
                    ),
                    Word(
                        id=2,
                        char="香港人",
                        code="390",
                        jyutping="hoeng1 gong2 jan4",
                        finals='["oeng","ong","an"]',
                        initials='["h","g","j"]',
                        length=3,
                    ),
                    Word(
                        id=3,
                        char="香港",
                        code="33",
                        jyutping="hoeng1 gong2",
                        finals='["oeng","ong"]',
                        initials='["h","g"]',
                        length=2,
                    ),
                ]
            )
            session.commit()

            triple = search_words(q="?港=?", mode="m1", db=session, limit=20, offset=0)
            literal = search_words(q="?港?", mode="m1", db=session, limit=20, offset=0)

        triple_chars = [r["char"] for r in triple]
        literal_chars = [r["char"] for r in literal]

        self.assertIn("香港人", triple_chars)
        self.assertNotIn("香港", triple_chars)
        self.assertIn("香港人", literal_chars)


class JyutpingAnchorParseTests(unittest.TestCase):
    def test_23ngo_is_anchor_not_fragment(self):
        from app.services.query_parse import JyutpingFragmentQuery

        parsed = _parse("23ngo")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertNotIsInstance(parsed, JyutpingFragmentQuery)
        self.assertEqual(parsed.anchor_pos, 1)
        self.assertEqual(parsed.anchor_value, "ngo")

    def test_3hon4_two_char_syllable(self):
        parsed = _parse("3hon4")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.width, 2)
        self.assertEqual(parsed.anchor_value, "hon")

    def test_3_question_hon4_three_char(self):
        parsed = _parse("3?hon4")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.anchor_pos, 1)


class JyutpingAnchorSearchTests(unittest.TestCase):
    def test_middle_rhyme_yut_finds_snow_word(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="下雪天",
                        code="334",
                        jyutping="haa6 syut3 tin1",
                        finals='["aa","ut","in"]',
                        initials='["h","s","t"]',
                        length=3,
                    ),
                    Word(
                        id=2,
                        char="下雨天",
                        code="334",
                        jyutping="haa6 jyu5 tin1",
                        finals='["aa","yu","in"]',
                        initials='["h","j","t"]',
                        length=3,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="?yut?", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("下雪天", chars)
        self.assertNotIn("下雨天", chars)

    def test_middle_syllable_syut(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="打雪仗",
                        code="333",
                        jyutping="daa2 syut3 zoeng3",
                        finals='["aa","ut","oeng"]',
                        initials='["d","s","z"]',
                        length=3,
                    ),
                    Word(
                        id=2,
                        char="打書包",
                        code="333",
                        jyutping="daa2 syu1 baau1",
                        finals='["aa","yu","au"]',
                        initials='["d","s","b"]',
                        length=3,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="?syut?", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("打雪仗", chars)
        self.assertNotIn("打書包", chars)

    def test_end_syllable_hon(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="北韓",
                        code="33",
                        jyutping="bak1 hon3",
                        finals='["ak","on"]',
                        initials='["b","h"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="香港",
                        code="33",
                        jyutping="hoeng1 gong2",
                        finals='["oeng","ong"]',
                        initials='["h","g"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="?hon", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("北韓", chars)
        self.assertNotIn("香港", chars)

    def test_23ngo_finds_ngo_last_syllable(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="呢我",
                        code="23",
                        jyutping="nei1 ngo5",
                        finals='["ei","o"]',
                        initials='["n","ng"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="呢你",
                        code="23",
                        jyutping="nei1 nei5",
                        finals='["ei","ei"]',
                        initials='["n","n"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            anchor_results = search_words(q="23ngo", mode="m1", db=session, limit=20, offset=0)

        anchor_chars = [r["char"] for r in anchor_results]
        self.assertIn("呢我", anchor_chars)
        self.assertNotIn("呢你", anchor_chars)

    def test_code_syllable_two_hon(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="韓流",
                        code="34",
                        jyutping="hon3 lau4",
                        finals='["on","au"]',
                        initials='["h","l"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="香爐",
                        code="34",
                        jyutping="hoeng1 lou4",
                        finals='["oeng","ou"]',
                        initials='["h","l"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="3hon4", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("韓流", chars)
        self.assertNotIn("香爐", chars)

    def test_23ei0_middle_rhyme_equals(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="二你零",
                        code="230",
                        jyutping="ji6 nei5 ling4",
                        finals='["i","ei","ing"]',
                        initials='["j","n","l"]',
                        length=3,
                    ),
                    Word(
                        id=2,
                        char="二我零",
                        code="230",
                        jyutping="ji6 ngo5 ling4",
                        finals='["i","o","ing"]',
                        initials='["j","n","l"]',
                        length=3,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="23ei0", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("二你零", chars)
        self.assertNotIn("二我零", chars)

    def test_3h4_initial_anchor(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="韓流",
                        code="34",
                        jyutping="hon3 lau4",
                        finals='["on","au"]',
                        initials='["h","l"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="根留",
                        code="34",
                        jyutping="kan4 lau4",
                        finals='["an","au"]',
                        initials='["k","l"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="3h4", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("韓流", chars)
        self.assertNotIn("根留", chars)

    def test_23o_rhyme_hybrid(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="呢坐",
                        code="23",
                        jyutping="nei1 co5",
                        finals='["ei","o"]',
                        initials='["n","c"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="呢你",
                        code="23",
                        jyutping="nei1 nei5",
                        finals='["ei","ei"]',
                        initials='["n","n"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="23o", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("呢坐", chars)
        self.assertNotIn("呢你", chars)


class JyutpingAnchorRejectTests(unittest.TestCase):
    def test_invalid_rhyme_anchor_rejected_not_fragment(self):
        from app.services.query_parse import JyutpingFragmentQuery, UnmatchedQuery

        parsed = _parse("?qxz?")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertNotIsInstance(parsed, JyutpingFragmentQuery)

    def test_invalid_rhyme_anchor_search_returns_hint(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database import Base
        from app.services.query_dispatch import (
            JYUTPING_ANCHOR_INVALID_HINT,
            SearchContext,
            execute_search,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            result = execute_search(
                SearchContext(
                    q="?qxz?",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=10,
                    offset=0,
                    db=session,
                )
            )

        self.assertEqual(result.items, [])
        self.assertEqual(result.hint, JYUTPING_ANCHOR_INVALID_HINT)


class RhymeFragmentMatchTests(unittest.TestCase):
    def test_single_letter_u_anchor_separates_u_and_yu(self):
        from app.services.jyutping_anchor import syllable_matches_rhyme_fragment

        self.assertTrue(syllable_matches_rhyme_fragment("fu", "u"))
        self.assertFalse(syllable_matches_rhyme_fragment("zyu", "u"))
        self.assertTrue(syllable_matches_rhyme_fragment("zyu", "yu"))

    def test_multi_letter_fragment_uses_suffix_match(self):
        from app.services.jyutping_anchor import syllable_matches_rhyme_fragment

        self.assertTrue(syllable_matches_rhyme_fragment("gong", "ong"))
        self.assertTrue(syllable_matches_rhyme_fragment("jyun", "yun"))


if __name__ == "__main__":
    unittest.main()
