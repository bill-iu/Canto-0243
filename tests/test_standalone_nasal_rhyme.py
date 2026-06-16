"""獨立韻母 m／ng 等價 — 韻母錨可互換，聲母 m／ng 不可。"""

import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.lexicon.reference_reading import anchor_phoneme_options
from app.models.word import Word
from app.services.position_match.filters import matches_phoneme_at_position
from app.services.query_dispatch import search_words
from app.utils.jyutping_codec import (
    expand_standalone_nasal_final_options,
    rhyme_final_index_keys_per_position,
    rhyme_final_tuples_compatible,
)


class InitialMNgNotEquivalentTests(unittest.TestCase):
    """聲母 m 與 ng 不得因韻母等價而混淆。"""

    def test_initial_n_anchor_does_not_match_ng_initial(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="娘流",
                        code="34",
                        jyutping="noeng4 lau4",
                        finals='["oeng","au"]',
                        initials='["n","l"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="我流",
                        code="34",
                        jyutping="ngo5 lau4",
                        finals='["o","au"]',
                        initials='["ng","l"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="3n4", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("娘流", chars)
        self.assertNotIn("我流", chars)


class InitialAnchorOptionsTests(unittest.TestCase):
    """錨點音素選項：initial 維度不得套用韻母 m／ng 等價。"""

    def _empty_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        return db

    def test_standalone_m_syllable_has_no_initial_anchor_options(self):
        opts = anchor_phoneme_options("唔", "initial", self._empty_db(), allow_inject=False)
        self.assertEqual(opts, set())

    def test_ngo_initial_options_exclude_m(self):
        opts = anchor_phoneme_options("我", "initial", self._empty_db(), allow_inject=False)
        self.assertIn("ng", opts)
        self.assertNotIn("m", opts)

    def test_matches_phoneme_initial_m_does_not_match_ng_word(self):
        db = self._empty_db()
        word_ng = Word(
            char="我",
            code="2",
            jyutping="ngo5",
            finals='[""]',
            initials='["ng"]',
            length=1,
        )
        self.assertFalse(
            matches_phoneme_at_position(word_ng, 0, "唔", constraint="initial", db=db)
        )


class StandaloneNasalRhymeCodecTests(unittest.TestCase):
    def test_mun_and_ngo_keep_normal_finals(self):
        keys = rhyme_final_index_keys_per_position("mun4 ngo5")
        self.assertEqual(keys[0], frozenset({"un"}))
        self.assertEqual(keys[1], frozenset({"o"}))

    def test_standalone_m_ng_rhyme_compatible(self):
        self.assertTrue(rhyme_final_tuples_compatible("m4", "ng5"))

    def test_expand_does_not_touch_unrelated_finals(self):
        self.assertEqual(expand_standalone_nasal_final_options({"un"}), {"un"})

    def test_expand_empty_with_other_final_does_not_add_nasal(self):
        """空韻母與一般韻母並存時，不得把 un 等誤當 m／ng 等價。"""
        self.assertEqual(expand_standalone_nasal_final_options({"", "un"}), {"", "un"})


class DualPhonemeAnchorSearchTests(unittest.TestCase):
    def test_3m4_dual_initial_and_final_columns(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="門人",
                        code="34",
                        jyutping="mun4 jan4",
                        finals='["un","an"]',
                        initials='["m","j"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="唔人",
                        code="34",
                        jyutping="m4 jan4",
                        finals='[""]',
                        initials='["m"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="3m4", mode="m1", db=session, limit=20, offset=0)

        by_dim = {}
        for row in results:
            by_dim.setdefault(row.get("anchor_dimension"), []).append(row["char"])
        self.assertIn("門人", by_dim.get("initial", []))
        self.assertNotIn("唔人", by_dim.get("initial", []))
        self.assertIn("唔人", by_dim.get("final", []))
        self.assertNotIn("門人", by_dim.get("final", []))

    def test_2ng0_dual_ngo_initial_and_nasal_final(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="我人",
                        code="20",
                        jyutping="ngo5 jan4",
                        finals='["o","an"]',
                        initials='["ng","j"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="五人",
                        code="20",
                        jyutping="ng5 jan4",
                        finals='[""]',
                        initials='["ng"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="2ng0", mode="m1", db=session, limit=20, offset=0)

        by_dim = {}
        for row in results:
            by_dim.setdefault(row.get("anchor_dimension"), []).append(row["char"])
        self.assertIn("我人", by_dim.get("initial", []))
        self.assertNotIn("五人", by_dim.get("initial", []))
        self.assertIn("五人", by_dim.get("final", []))

    def test_question_m_question_dual_middle_slot(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="問門人",
                        jyutping="man6 mun4 jan4",
                        finals='["an","un","an"]',
                        initials='["m","m","j"]',
                        length=3,
                    ),
                    Word(
                        id=2,
                        char="問唔人",
                        jyutping="man6 m4 jan4",
                        finals='["an","","an"]',
                        initials='["m","m","j"]',
                        length=3,
                    ),
                    Word(
                        id=3,
                        char="問行人",
                        jyutping="man6 hang4 jan4",
                        finals='["an","ang","an"]',
                        initials='["m","h","j"]',
                        length=3,
                    ),
                ]
            )
            session.commit()
            results = search_words(q="?m?", mode="m1", db=session, limit=20, offset=0)

        by_dim = {}
        for row in results:
            by_dim.setdefault(row.get("anchor_dimension"), []).append(row["char"])
        self.assertIn("問門人", by_dim.get("initial", []))
        self.assertNotIn("問唔人", by_dim.get("initial", []))
        self.assertIn("問唔人", by_dim.get("final", []))
        self.assertNotIn("問門人", by_dim.get("final", []))
        self.assertNotIn("問行人", by_dim.get("initial", []))
        self.assertNotIn("問行人", by_dim.get("final", []))


if __name__ == "__main__":
    unittest.main()
