"""單 digit 純碼：只以每字最佳 pron_rank 讀音入選（剔罕見／錯讀噪音）。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.lexicon.rime_char_index import load_rime_char_csv, reset_rime_char_for_tests
from app.models.word import Word
from app.services.position_match.filters.f1_slot_code import (
    filter_single_digit_to_preferred_readings,
)
from app.services.word_lookup_executor import WordLookupExecutor
from app.utils.jyutping_codec import get_code_variants
from tests.smoke.helpers import LYRICS_DB, lyrics_sessionmaker, memory_sessionmaker


class FilterSingleDigitPreferredUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rime_char_for_tests()
        csv = (
            "char,jyutping,pron_rank,hint_pinyin,hint_en\n"
            "湯,joeng4,罕見,,,\n"
            "湯,soeng1,棄用,,,\n"
            "湯,tong1,預設,,,\n"
            "湯,tong3,罕見,,,\n"
            "一,jat1,預設,,,\n"
        )
        self._tmp = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".csv", delete=False
        )
        self._tmp.write(csv)
        self._tmp.close()
        load_rime_char_csv(self._tmp.name)

    def tearDown(self) -> None:
        reset_rime_char_for_tests()
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_0_excludes_湯_rare_joeng4(self):
        rows = [
            Word(char="湯", code="0", jyutping="joeng4", length=1),
            Word(char="湯", code="3", jyutping="tong1", length=1),
            Word(char="湯", code="3", jyutping="soeng1", length=1),
            Word(char="湯", code="4", jyutping="tong3", length=1),
            Word(char="一", code="3", jyutping="jat1", length=1),
        ]
        variants = set(get_code_variants("0", "m1"))
        out = filter_single_digit_to_preferred_readings(rows, code_variants=variants)
        chars = {w.char for w in out}
        self.assertNotIn("湯", chars)

    def test_3_includes_湯_as_tong1(self):
        rows = [
            Word(char="湯", code="0", jyutping="joeng4", length=1),
            Word(char="湯", code="3", jyutping="tong1", length=1),
            Word(char="湯", code="3", jyutping="soeng1", length=1),
            Word(char="湯", code="4", jyutping="tong3", length=1),
        ]
        variants = set(get_code_variants("3", "m1"))
        out = filter_single_digit_to_preferred_readings(rows, code_variants=variants)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].char, "湯")
        self.assertEqual(out[0].jyutping, "tong1")

    def test_only_rare_still_admitted(self):
        """字只有罕見讀時，罕見即為最佳 → 仍可出。"""
        reset_rime_char_for_tests()
        csv = "char,jyutping,pron_rank,hint_pinyin,hint_en\n冷,laang5,罕見,,,\n"
        path = Path(self._tmp.name)
        path.write_text(csv, encoding="utf-8")
        load_rime_char_csv(path)
        rows = [Word(char="冷", code="5", jyutping="laang5", length=1)]
        variants = set(get_code_variants("5", "m1"))
        out = filter_single_digit_to_preferred_readings(rows, code_variants=variants)
        self.assertEqual([w.char for w in out], ["冷"])


class PureDigitExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rime_char_for_tests()
        csv = (
            "char,jyutping,pron_rank,hint_pinyin,hint_en\n"
            "湯,joeng4,罕見,,,\n"
            "湯,tong1,預設,,,\n"
        )
        self._tmp = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".csv", delete=False
        )
        self._tmp.write(csv)
        self._tmp.close()
        load_rime_char_csv(self._tmp.name)

    def tearDown(self) -> None:
        reset_rime_char_for_tests()
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_pure_digit_0_excludes_湯(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="湯", code="0", jyutping="joeng4", length=1),
                Word(id=2, char="湯", code="3", jyutping="tong1", length=1),
                Word(id=3, char="和", code="0", jyutping="wo4", length=1),
            ])
            db.commit()
            # 和 only one reading → admitted for 0
            reset_rime_char_for_tests()
            Path(self._tmp.name).write_text(
                "char,jyutping,pron_rank,hint_pinyin,hint_en\n"
                "湯,joeng4,罕見,,,\n"
                "湯,tong1,預設,,,\n"
                "和,wo4,預設,,,\n",
                encoding="utf-8",
            )
            load_rime_char_csv(self._tmp.name)
            items, total = WordLookupExecutor(db).pure_digit("0", None, "m1", 50, 0)
        chars = [it["char"] for it in items]
        self.assertNotIn("湯", chars)
        self.assertIn("和", chars)
        self.assertEqual(total, len(items))

    def test_multi_digit_no_preferred_gate(self):
        """len≥2 唔套 preferred 閘（靠 essay 沉底）。"""
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="AB", code="00", jyutping="aa1 bei1", length=2),
            ])
            db.commit()
            items, _ = WordLookupExecutor(db).pure_digit("00", None, "m1", 50, 0)
        self.assertEqual([it["char"] for it in items], ["AB"])


@unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
class SingleDigitLyricsRegressionTests(unittest.TestCase):
    def test_0_excludes_湯_tong1_is_default(self):
        Session = lyrics_sessionmaker()
        with Session() as db:
            items, _ = WordLookupExecutor(db).pure_digit("0", None, "m1", 800, 0)
            items3, _ = WordLookupExecutor(db).pure_digit("3", None, "m1", 800, 0)
        chars0 = {it["char"] for it in items}
        chars3 = {it["char"] for it in items3}
        self.assertNotIn("湯", chars0)
        tong = [it for it in items3 if it["char"] == "湯"]
        self.assertTrue(tong, "湯 should appear under 3")
        self.assertEqual(tong[0]["jyutping"], "tong1")


if __name__ == "__main__":
    unittest.main()
