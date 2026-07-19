"""ADR-0051 §3 — 錨點選項剔罕見／棄用 pron_rank；語境錨點唔剔。"""
from __future__ import annotations

import unittest

from app.domain.lexicon.reference_reading import anchor_phoneme_options
from app.lexicon.rime_char_index import PRON_RANK_SORT, load_rime_char_csv
from app.models.word import Word
from app.services.position_match.filters import contextual_final_options_at_position
from tests.smoke.helpers import LYRICS_DB, lyrics_sessionmaker, memory_sessionmaker


class AnchorPhonemeOptionsPronRankTests(unittest.TestCase):
    def test_難_anchor_finals_exclude_rare_no4(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(char="難", code="0", jyutping="naan4", finals='["aan"]', length=1),
                Word(char="難", code="0", jyutping="no4", finals='["o"]', length=1),
            ])
            db.commit()
            opts = anchor_phoneme_options("難", "final", db, allow_inject=False)
        self.assertIn("aan", opts)
        self.assertNotIn("o", opts)

    def test_潦_anchor_finals_include_common_lou5(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(char="潦", code="9", jyutping="liu2", finals='["iu"]', length=1),
                Word(char="潦", code="5", jyutping="lou5", finals='["ou"]', length=1),
            ])
            db.commit()
            opts = anchor_phoneme_options("潦", "final", db, allow_inject=False)
        self.assertIn("iu", opts)
        self.assertIn("ou", opts)

    def test_unknown_pron_rank_stays_in_anchor_union(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add(Word(char="測", code="11", jyutping="mak6", finals='["ak"]', length=1))
            db.commit()
            opts = anchor_phoneme_options("測", "final", db, allow_inject=False)
        self.assertIn("ak", opts)

    def test_棄用_label_is_known_pron_rank(self):
        self.assertEqual(PRON_RANK_SORT["棄用"], 3)
        n = load_rime_char_csv()
        self.assertGreater(n, 0)


class ContextualAnchorOptionsTests(unittest.TestCase):
    def test_contextual_潦_includes_ou_from_compound_reading(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add(
                Word(
                    char="貧窮潦倒",
                    code="0449",
                    jyutping="pan4 kung4 lou5 dou2",
                    finals='["an", "ung", "ou", "ou"]',
                    length=4,
                )
            )
            db.commit()
            opts = contextual_final_options_at_position(db, 4, 2, "潦")
        self.assertIn("ou", opts)


@unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
class AnchorPhonemeOptionsLyricsRegressionTests(unittest.TestCase):
    def test_難_anchor_on_lyrics_excludes_o(self):
        Session = lyrics_sessionmaker()
        with Session() as db:
            opts = anchor_phoneme_options("難", "final", db, allow_inject=False)
        self.assertNotIn("o", opts)
        self.assertIn("aan", opts)

    def test_信_anchor_on_lyrics_excludes_deprecated_an(self):
        """棄用 san1 唔入錨點；34信 唔應因 an 命中吸引／幫襯。"""
        load_rime_char_csv()
        Session = lyrics_sessionmaker()
        with Session() as db:
            opts = anchor_phoneme_options("信", "final", db, allow_inject=False)
        self.assertNotIn("an", opts)
        self.assertIn("eon", opts)


if __name__ == "__main__":
    unittest.main()