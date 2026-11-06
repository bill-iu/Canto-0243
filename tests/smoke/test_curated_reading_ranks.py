"""Curated whole-word grades share the existing ranking contract across runtimes."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.domain.lexicon.ranking import authoritative_reading_sort_key, search_result_sort_key
from app.lexicon.rime_char_index import (
    PRON_RANK_SORT, load_rime_char_csv, load_word_pron_ranks,
    pron_rank_sort_value, pron_rank_sort_value_for_word, reset_rime_char_for_tests,
)
from app.utils.trad_chinese import to_traditional
from app.utils.jyutping_codec import get_0243_code
from app.utils.word_cache import reset_word_cache_for_tests
from app.models.word import Word
from app.services.word_lookup_executor import WordLookupExecutor

ROOT = Path(__file__).resolve().parents[2]
RANKS = ROOT / "data/lexicon/curated_reading_ranks.json"


class CuratedReadingRankTests(unittest.TestCase):
    def setUp(self):
        reset_rime_char_for_tests()

    def tearDown(self):
        reset_rime_char_for_tests()

    def test_every_curated_reading_has_a_traceable_grade(self):
        source = ROOT / "data/lexicon/curated_lexicon.json"
        rime = ROOT / "data/rime/char.csv"
        rows = json.loads(RANKS.read_text(encoding="utf-8"))
        meta = json.loads(RANKS.with_suffix(".meta.json").read_text(encoding="utf-8"))
        curated = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), meta["curated_rows"])
        self.assertEqual(len(rows), len(curated))
        self.assertEqual({(r["char"], r["jyutping"]) for r in rows}, {(r["char"], r["jyutping"]) for r in curated})
        self.assertEqual(meta["curated_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        # CI deliberately installs the tracked small character fixture. Only
        # that exact file may omit the full-source provenance comparison.
        full_rime = rime.read_bytes() != (ROOT / "data/rime/fixtures/char_sample.csv").read_bytes()
        if full_rime:
            self.assertEqual(meta["rime_char_sha256"], hashlib.sha256(rime.read_bytes()).hexdigest())
        self.assertEqual(meta["ranks_sha256"], hashlib.sha256(RANKS.read_bytes()).hexdigest())
        with rime.open(encoding="utf-8", newline="") as handle:
            chars = {(r["char"], r["jyutping"]): PRON_RANK_SORT.get(r["pron_rank"], 99) for r in csv.DictReader(handle)}
        aliases = meta["orthographic_aliases"]
        loaded = load_word_pron_ranks(RANKS)
        for row in rows:
            with self.subTest(char=row["char"], jyutping=row["jyutping"]):
                actual = to_traditional(row["char"])
                self.assertEqual(row["ingested_char"], actual)
                self.assertIn(row["pron_rank"], PRON_RANK_SORT)
                original = [chars.get((c, s), 99) for c, s in zip(actual, row["jyutping"].split())]
                if full_rime:
                    self.assertEqual(row["component_rank"], max(original))
                self.assertEqual(loaded[actual, row["jyutping"]], PRON_RANK_SORT[row["pron_rank"]])
                self.assertTrue(row["note"])
                if row["basis"] == "rime-components":
                    self.assertEqual(PRON_RANK_SORT[row["pron_rank"]], row["component_rank"])
                elif row["basis"] == "rime-orthographic":
                    inherited = [chars.get((aliases.get(c, c), s), 99) if v == 99 else v
                                 for c, s, v in zip(actual, row["jyutping"].split(), original)]
                    if full_rime:
                        self.assertEqual(PRON_RANK_SORT[row["pron_rank"]], max(inherited))
                else:
                    self.assertEqual(row["basis"], "ai-context")
                    self.assertEqual(row["evidence"], "AI:whole-word-context")

    def test_word_context_overrides_do_not_change_character_grades(self):
        original_char_grade = pron_rank_sort_value("會", "wui2")
        self.assertEqual(pron_rank_sort_value_for_word("社會保障", "se5 wui2 bou2 zoeng3"), 0)
        self.assertEqual(pron_rank_sort_value_for_word("從容應對", "sung1 jung4 jing3 deoi3"), 1)
        self.assertEqual(pron_rank_sort_value_for_word("利潤率", "lei6 jeon6 leot6"), 1)
        self.assertEqual(pron_rank_sort_value_for_word("無縫", "mou4 fung6"), 1)
        self.assertEqual(pron_rank_sort_value_for_word("報名點", "bou3 meng2 dim2"), 0)
        self.assertEqual(pron_rank_sort_value_for_word("槓子", "gong3 zi2"), 0)
        self.assertEqual(pron_rank_sort_value_for_word("天呀", "tin1 aa3"), 0)
        self.assertEqual(pron_rank_sort_value_for_word("吧嗒", "baa1 taap3"), 0)
        self.assertEqual(pron_rank_sort_value_for_word("聽不見", "ting1 bat1 gin3"), 2)
        self.assertEqual(pron_rank_sort_value_for_word("衝着", "cung3 zoek6"), 3)
        for text in ("弱勢社群", "弱勢社羣"):
            self.assertEqual(pron_rank_sort_value_for_word(text, "joek6 sai3 se5 kwan4"), 0)
        self.assertEqual(pron_rank_sort_value_for_word("會", "wui2"), original_char_grade)
        self.assertEqual(pron_rank_sort_value_for_word("不存在", "bat1"), 99)

    def test_search_and_reference_reading_order_uses_word_grades(self):
        # A historical word reading must retain its inherited rare grade.
        self.assertEqual(pron_rank_sort_value_for_word("桀驁不馴", "git6 ngou6 bat1 seon4"), 2)
        cases = {
            "長於": ("zoeng2 jyu1", "coeng4 jyu1"),
            "首尾相連": ("sau2 mei5 soeng1 lin4", "sau2 mei2 soeng1 lin4"),
            "鈾礦": ("jau2 kwong3", "jau4 kwong3"),
            "烷基": ("jyun2 gei1", "jyun4 gei1"),
            "懷揣": ("waai4 caai1", "waai4 cyun2"),
            "水磨": ("seoi2 mo6", "seoi2 mo4"),
            "蘆蓆": ("lou4 zek6", "lou4 zik6"),
            "生澀": ("saang1 gip3", "sang1 gip3"),
            "筆墨紙硯": ("bat1 mak6 zi2 jin6", "bat1 mak6 zi2 jin2"),
            "締合": ("dai3 hap6", "tai3 hap6"),
            "血泡": ("hyut3 pok1", "hyut3 paau3"),
            "螺鈿": ("lo4 din6", "lo4 tin4"),
            "外差": ("ngoi6 caai1", "ngoi6 caa1"),
            "凹版": ("nap1 baan2", "aau1 baan2"),
            "令妹": ("ling6 mui2", "ling6 mui6"),
            "繾綣": ("hin2 hyun2", "hin2 hyun3"),
            "校勘學": ("gaau3 ham3 hok6", "gaau3 ham1 hok6"),
            "指畫": ("zi2 waa2", "zi2 waak6"),
            "露餡": ("lou6 haam2", "lou6 haam6"),
            "吼叫聲": ("haau1 giu3 sing1", "hau3 giu3 sing1"),
            "跛行": ("bai1 haang4", "bo2 hang4"),
            "種糧": ("zung2 loeng4", "zung3 loeng4"),
            "登記簿": ("dang1 gei3 bou2", "dang1 gei3 bou6"),
            "水松": ("seoi2 sung1", "seoi2 cung4"),
            "會員卡": ("wui6 jyun4 kaa1", "wui2 jyun4 kaa1"),
            "曖昧關係": ("oi3 mui6 gwaan1 hai6", "oi2 mui6 gwaan1 hai6"),
            "竹蓆": ("zuk1 zek6", "zuk1 zik6"),
            "右衽": ("jau6 jam6", "jau6 jam5"),
            "彈球": ("taan4 kau4", "daan2 kau4"),
            "毛巾被": ("mou4 gan1 bei2", "mou4 gan1 bei6"),
            "休息廳": ("jau1 sik1 teng1", "jau1 sik1 ting1"),
            "跳跳蹦蹦": ("tiu3 tiu3 bang1 bang1", "tiu3 tiu3 baang6 baang6"),
            "儀表板": ("ji4 biu2 baan2", "ji4 biu1 baan2"),
            "去核": ("heoi3 wat6", "heoi3 hat6"),
            "報名處": ("bou3 meng2 cyu3", "bou3 ming4 cyu3"),
            "嵌合體": ("ham3 hap6 tai2", "ham6 hap6 tai2"),
            "梳篦": ("so1 bei6", "so1 bei1"),
            "廳局級": ("ting1 guk6 kap1", "teng1 guk6 kap1"),
            "腺嘌呤": ("sin3 piu1 ling4", "sin3 piu3 ling6"),
            "拙著": ("zyut3 zyu3", "zyut6 zyu3"),
            "肉鴿": ("juk6 gap3", "juk6 gaap3"),
            "聾啞學校": ("lung4 aa2 hok6 haau6", "lung4 ngaa2 hok6 haau6"),
            "塑料瓶": ("sou3 liu2 ping4", "sok3 liu2 ping4"),
            "桀驁不馴": ("git6 ngou4 bat1 seon4", "git6 ngou6 bat1 seon4"),
            "酵解": ("haau1 gaai2", "gaau3 gaai2"),
            "倩女": ("sin6 neoi5", "sin3 neoi5"),
            "外廓": ("ngoi6 kwok3", "ngoi6 gwok3"),
            "金錠": ("gam1 ding6", "gam1 ding3"),
            "冥界": ("ming5 gaai3", "ming4 gaai3"),
            "條件性": ("tiu4 gin2 sing3", "tiu4 gin6 sing3"),
            "露相": ("lau6 soeng3", "lou6 soeng3"),
            "鐵板釘釘": ("tit3 baan2 deng1 deng1", "tit3 baan2 ding3 ding1"),
            "鴨肫": ("aap3 zeon1", "aap3 san5"),
            "銘心": ("ming5 sam1", "ming4 sam1"),
            "鮑魚之肆": ("baau6 jyu4 zi1 si3", "baau1 jyu4 zi1 si3"),
            "茜素": ("sin6 sou3", "sin3 sou3"),
            "黏稠度": ("nim1 cau4 dou6", "nim4 cau4 dou6"),
            "滴鼻": ("dik1 bei6", "dik6 bei6"),
            "夜靜更深": ("je6 zing6 gaang1 sam1", "je6 zing6 gang1 sam1"),
            "塑料膜": ("sou3 liu2 mok6", "sok3 liu2 mok2"),
        }
        for char, (preferred, variant) in cases.items():
            rows = [SimpleNamespace(char=char, jyutping=jp) for jp in (variant, preferred)]
            for key in (search_result_sort_key, authoritative_reading_sort_key):
                with self.subTest(char=char, sort=key.__name__):
                    self.assertEqual(sorted(rows, key=key)[0].jyutping, preferred)

    def test_explicit_payload_root_and_missing_legacy_file_keep_char_fallback(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            char_csv = data / "rime/char.csv"
            char_csv.parent.mkdir(parents=True)
            char_csv.write_text("char,jyutping,pron_rank\n社,se5,預設\n會,wui2,罕見\n", encoding="utf-8")
            load_rime_char_csv(char_csv)
            self.assertEqual(pron_rank_sort_value_for_word("社會", "se5 wui2"), 2)
            path = data / "lexicon/curated_reading_ranks.json"
            path.parent.mkdir()
            path.write_text(json.dumps([dict(char="社會", jyutping="se5 wui2", pron_rank="常用")]), encoding="utf-8")
            reset_rime_char_for_tests()
            load_rime_char_csv(char_csv)
            self.assertEqual(pron_rank_sort_value_for_word("社會", "se5   wui2"), 1)

    def test_literal_lookup_chooses_preferred_reading_before_merging_word_cards(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
        reset_word_cache_for_tests()
        try:
            with Session(engine) as db:
                for char, preferred, variant in [
                    ("長於", "zoeng2 jyu1", "coeng4 jyu1"),
                    ("首尾相連", "sau2 mei5 soeng1 lin4", "sau2 mei2 soeng1 lin4"),
                    ("蘆蓆", "lou4 zek6", "lou4 zik6"),
                    ("締合", "dai3 hap6", "tai3 hap6"),
                    ("螺鈿", "lo4 din6", "lo4 tin4"),
                    ("血泡", "hyut3 pok1", "hyut3 paau3"),
                    ("令妹", "ling6 mui2", "ling6 mui6"),
                    ("繾綣", "hin2 hyun2", "hin2 hyun3"),
                    ("指畫", "zi2 waa2", "zi2 waak6"),
                    ("跛行", "bai1 haang4", "bo2 hang4"),
                    ("水松", "seoi2 sung1", "seoi2 cung4"),
                    ("會員卡", "wui6 jyun4 kaa1", "wui2 jyun4 kaa1"),
                ]:
                    # Older variant is deliberately inserted first.
                    for jp in (variant, preferred):
                        db.add(Word(char=char, jyutping=jp, code=get_0243_code(jp), length=len(char)))
                    db.commit()
                    items, _ = WordLookupExecutor(db).pure_canto(char, None, "m3", 100, 0)
                    exact = [row for row in items if row["char"] == char]
                    self.assertEqual(len(exact), 1)
                    self.assertEqual(exact[0]["jyutping"], preferred)
        finally:
            reset_word_cache_for_tests()
            engine.dispose()

    def test_invalid_or_conflicting_word_grades_fail_clearly(self):
        valid = dict(char="群山", ingested_char="羣山", jyutping="kwan4 saan1", pron_rank="預設")
        invalid = [None, {}, [None], [dict(valid, pron_rank=99)], [dict(valid, pron_rank=["預設"])],
                   [dict(valid, char="群")], [dict(valid, jyutping="kwan7 saan1")],
                   [valid, dict(valid, char="羣山", pron_rank="常用")]]
        with TemporaryDirectory() as tmp:
            for i, rows in enumerate(invalid):
                path = Path(tmp) / f"{i}.json"
                path.write_text(json.dumps(rows), encoding="utf-8")
                with self.subTest(rows=rows), self.assertRaises(ValueError):
                    load_word_pron_ranks(path)


if __name__ == "__main__":
    unittest.main()
