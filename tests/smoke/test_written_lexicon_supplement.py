"""Reviewed written expressions retain provenance and survive normal ingest/search."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import load_corrections
from app.services.query_dispatch import QueryEngine, SearchContext
from app.utils.jyutping_codec import get_0243_code
from app.utils.trad_chinese import to_traditional
from app.utils.word_cache import reset_word_cache_for_tests
from ingest.lexicon_build import persist_lexicon_candidates
from ingest.lexicon_sources import ingest_lexicon_json
from ingest.lexicon_overlay import apply_lexicon_overlay

ROOT = Path(__file__).resolve().parents[2]
CURATED = ROOT / "data/lexicon/curated_lexicon.json"
REVIEW = ROOT / "data/lexicon/reviews/2026-11-06-written-supplement.tsv"
META = ROOT / "data/lexicon/reviews/2026-11-06-written.meta.json"
BATCH = "2026-11-06-written"
BATCH_02 = "2026-11-06-written-b02"
BATCH_03 = "2026-11-06-written-b03"
BATCH_04 = "2026-11-06-written-b04"
BATCH_05 = "2026-11-06-written-b05"
BATCH_06 = "2026-11-06-written-b06"
BATCH_07 = "2026-11-06-written-b07"
BATCH_08 = "2026-11-06-written-b08"
BATCH_09 = "2026-11-06-written-b09"
BATCH_10 = "2026-11-06-written-b10"


def review_rows(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")), delimiter="\t"))


def batch_number(path):
    match = re.search(r"-b(\d+)-", path.name)
    return int(match.group(1)) if match else 0


def repair_ledgers():
    return sorted(REVIEW.parent.glob("2026-11-06-written*-supplement.tsv"), key=batch_number)


def input_fingerprint(curated, meta, batch):
    """Undo only later, explicitly documented reading/code changes in this prefix."""
    prefix = json.loads(json.dumps(curated[:meta["input_curated_rows"]]))
    for path in reversed(repair_ledgers()):
        if batch_number(path) < batch:
            continue
        for row in reversed(review_rows(path)):
            if row["verdict"] != "repair":
                continue
            for old in prefix:
                if (old["char"], old.get("evidence"), old["jyutping"]) == (row["char"], row["evidence"], row["jyutping"]):
                    old["jyutping"] = row["previous_jyutping"]
                    old["code"] = get_0243_code(row["previous_jyutping"])
    serialized = json.dumps(prefix, ensure_ascii=False, indent=2) + "\n"
    return hashlib.sha256(serialized.encode()).hexdigest()


def apply_recorded_repairs(accepted):
    """A later correction must name the exact prior reading and evidence."""
    for path in repair_ledgers():
        for row in review_rows(path):
            if row["verdict"] != "repair" or not row["evidence"].startswith("jieba:"):
                continue
            prior = (row["char"], row["previous_jyutping"], get_0243_code(row["previous_jyutping"]), row["evidence"])
            if prior in accepted:
                accepted.remove(prior)
                accepted.add((row["char"], row["jyutping"], row["code"], row["evidence"]))
    return accepted


class WrittenLexiconSupplementTests(unittest.TestCase):
    def test_only_explicit_accepts_are_promoted_and_source_rows_remain_traceable(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        meta = json.loads(META.read_text(encoding="utf-8"))
        review = review_rows(REVIEW)
        batch = [row for row in curated if row.get("batch") == BATCH]
        self.assertEqual(hashlib.sha256(REVIEW.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["reviewed_candidates"])
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertGreater(len(batch), 3500)
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        accepted = apply_recorded_repairs(accepted)
        self.assertEqual(accepted, {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        sources = {row["path"] for row in meta["source_files"]}
        for row in review:
            with self.subTest(row["char"]):
                self.assertIn(row["source_file"], sources)
                self.assertGreater(int(row["source_line"]), 0)
                self.assertEqual(row["evidence"], f"jieba:{meta['source_commit']}:{row['source_file']}#L{row['source_line']}")
                if row["verdict"] != "accept":
                    self.assertFalse(row["jyutping"] or row["code"])
        # The previous source is preserved, including its review metadata and repairs.
        prefix = json.dumps(curated[:meta["input_curated_rows"]], ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(), meta["input_curated_sha256"])
        literals = {row["char"] for row in batch}
        self.assertTrue(literals.isdisjoint({"瞧瞧", "哥兒倆", "倒騰", "今兒個", "令狐沖笑", "打狗棒法", "子丑寅卯", "窗明几淨"}))
        for row in curated:
            for char, syllable in zip(row["char"], row["jyutping"].split()):
                if char == "病":
                    self.assertEqual(syllable, "beng6")

    def test_continuation_records_promotions_and_explicit_repairs(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_02}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_02}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        batch = [row for row in curated if row.get("batch") == BATCH_02]
        self.assertEqual(len(batch), meta["added_rows"])
        literals = {row["char"] for row in batch}
        self.assertTrue({"親征", "東征", "抗干擾", "窗明几淨", "子丑寅卯", "洋面", "郁郁", "覆議", "多複變"}.issubset(literals))
        self.assertTrue(literals.isdisjoint({"親徵", "東徵", "抗幹擾", "窗明幾淨", "子醜寅卯", "洋麪", "鬱郁", "複議", "多復變"}))
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        # Reverse only documented reading/code edits: all other previous fields
        # and row order must still match the input fingerprint.
        repairs = [row for row in review if row["verdict"] == "repair"]
        self.assertEqual(len(repairs), meta["reading_repairs"])
        self.assertEqual(input_fingerprint(curated, meta, 2), meta["input_curated_sha256"])
        self.assertEqual({row["jyutping"] for row in batch if row["char"] == "長於"}, {"zoeng2 jyu1", "coeng4 jyu1"})

    def test_contextual_normalization_preserves_word_senses_on_reingest(self):
        cases = {
            "长征": "長征", "長征": "長征", "親征": "親征", "東征": "東征",
            "干系": "干係", "干係": "干係", "抗干扰": "抗干擾", "抗干擾": "抗干擾",
            "干預": "干預", "斗转星移": "斗轉星移", "斗轉星移": "斗轉星移",
            "窗明几净": "窗明几淨", "窗明几淨": "窗明几淨", "子丑寅卯": "子丑寅卯",
            "洋面": "洋面", "郁郁": "郁郁",
            "干扰素": "干擾素", "干擾素": "干擾素",
            "里长": "里長", "里長": "里長", "裏長": "里長",
            "栗钙土": "栗鈣土", "栗鈣土": "栗鈣土", "慄鈣土": "栗鈣土",
            "同里": "同里", "同裏": "同里",
            "征辟": "徵辟", "徵辟": "徵辟", "徵闢": "徵辟",
            "报名表": "報名表", "報名表": "報名表", "報名錶": "報名表",
            "头面人物": "頭面人物", "頭面人物": "頭面人物", "頭麪人物": "頭面人物",
            "划手": "划手", "劃手": "划手",
            "机械系": "機械系", "機械系": "機械系", "機械繫": "機械系",
            "干扰机": "干擾機", "干擾機": "干擾機", "幹擾機": "干擾機",
            "斗式": "斗式", "鬥式": "斗式",
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                self.assertEqual(to_traditional(original), expected)
                self.assertEqual(to_traditional(expected), expected)
        for unchanged in ("幹部", "干支", "徵求", "象徵", "鬥爭", "幾何", "醜態", "洋麵", "鬱鬱", "憂鬱", "這裏", "闢謠", "手錶", "麪粉", "劃分", "劃界", "繫帶", "幹事", "鬥牛"):
            with self.subTest(unchanged=unchanged):
                self.assertEqual(to_traditional(unchanged), unchanged)

    def test_third_batch_is_reviewed_and_preserves_the_previous_source(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_03}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_03}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        batch = [row for row in curated if row.get("batch") == BATCH_03]
        self.assertEqual(len(batch), meta["added_rows"])
        expected = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(expected), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        self.assertEqual(input_fingerprint(curated, meta, 3), meta["input_curated_sha256"])
        self.assertNotIn("defer", {row["verdict"] for row in review})
        self.assertTrue({"拍賣行", "靈長類", "干擾素", "冰月", "中保", "樂藝"}.issubset({row["char"] for row in batch}))

    def test_fourth_batch_records_only_explicit_reading_repairs_and_alternatives(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_04}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_04}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(sum(row["verdict"] == "repair" for row in review), meta["reading_repairs"])
        self.assertEqual(input_fingerprint(curated, meta, 4), meta["input_curated_sha256"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        batch = [row for row in curated if row.get("batch") == BATCH_04]
        self.assertEqual(len(batch), meta["added_readings"])
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        pairs = {(row["char"], row["jyutping"], row["code"]) for row in curated}
        for row in review:
            self.assertIn((row["char"], row["jyutping"], row["code"]), pairs)
            if row["verdict"] == "repair":
                self.assertNotIn((row["char"], row["previous_jyutping"], get_0243_code(row["previous_jyutping"])), pairs)

    def test_contextual_readings_and_codes_survive_ingest_and_search(self):
        cases = {
            "這種": ("ze5 zung2", "59"),
            "不復存在": ("bat1 fuk6 cyun4 zoi6", "3202"),
            "擦肩而過": ("caat3 gin1 ji4 gwo3", "4304"),
            "合二為一": ("hap6 ji6 wai4 jat1", "2203"),
            "冠狀動脈": ("gun1 zong6 dung6 mak6", "3222"),
            "從容應對": ("sung1 jung4 jing3 deoi3", "3044"),
            "生命科學": ("sang1 ming6 fo1 hok6", "3232"),
            "利潤率": ("lei6 jeon6 leot6", "222"),
            "行長": ("hong4 zoeng2", "09"),
            "年老多病": ("nin4 lou5 do1 beng6", "0532"),
            "太重": ("taai3 cung5", "45"),
            "不堪重負": ("bat1 ham1 cung5 fu6", "3352"),
            "轉入": ("zyun2 jap6", "92"),
            "話鋒一轉": ("waa6 fung1 jat1 zyun2", "2339"),
            "親征": ("can1 zing1", "33"),
            "抗干擾": ("kong3 gon1 jiu2", "439"),
            "窗明几淨": ("coeng1 ming4 gei1 zing6", "3032"),
            "子丑寅卯": ("zi2 cau2 jan4 maau5", "9905"),
            "洋面": ("joeng4 min6", "02"),
            "郁郁": ("juk1 juk1", "33"),
            "覆議": ("fuk1 ji5", "35"),
            "多複變": ("do1 fuk1 bin3", "334"),
            "消費量": ("siu1 fai3 loeng6", "342"),
            "上表": ("soeng5 biu2", "59"),
            "重劍": ("cung5 gim3", "54"),
            "汞柱": ("hung3 cyu5", "45"),
            "拍賣行": ("paak3 maai6 hong4", "420"),
            "靈長類": ("ling4 zoeng2 leoi6", "092"),
            "干擾素": ("gon1 jiu2 sou3", "394"),
            "生長期": ("sang1 zoeng2 kei4", "390"),
            "重力場": ("cung5 lik6 coeng4", "520"),
            "相中": ("soeng1 zung3", "34"),
            "糖分": ("tong4 fan6", "02"),
            "中保": ("zung1 bou2", "39"),
            "處方藥": ("cyu2 fong1 joek6", "932"),
            "藏醫": ("zong6 ji1", "23"),
            "陀螺儀": ("to4 lo4 ji4", "000"),
            "聲色俱厲": ("sing1 sik1 keoi1 lai6", "3332"),
            "一榮俱榮": ("jat1 wing4 keoi1 wing4", "3030"),
            "一損俱損": ("jat1 syun2 keoi1 syun2", "3939"),
            "泥沙俱下": ("nai4 saa1 keoi1 haa6", "0332"),
            "不自禁": ("bat1 zi6 gam3", "324"),
            "與會者": ("jyu5 wui6 ze2", "529"),
            "沒空": ("mut6 hung1", "23"),
            "首尾相連": ("sau2 mei5 soeng1 lin4", "9530"),
            "鈾礦": ("jau2 kwong3", "94"),
            "烷基": ("jyun2 gei1", "93"),
            "艇長": ("teng5 zoeng2", "59"),
            "點將": ("dim2 zoeng3", "94"),
            "上半時": ("soeng6 bun3 si4", "240"),
            "上週五": ("soeng6 zau1 ng5", "235"),
            "形相": ("jing4 soeng3", "04"),
            "應激": ("jing3 gik1", "43"),
            "步行者": ("bou6 hang4 ze2", "209"),
            "老宅": ("lou5 zaak6", "52"),
            "群峯": ("kwan4 fung1", "03"),
            "槓子": ("gong3 zi2", "49"),
            "金石學": ("gam1 sek6 hok6", "322"),
            "調處": ("tiu4 cyu2", "09"),
            "間作": ("gaan3 zok3", "44"),
            "單行本": ("daan1 hang4 bun2", "309"),
            "間冰期": ("gaan3 bing1 kei4", "430"),
            "塞上": ("coi3 soeng6", "42"),
            "進藏": ("zeon3 zong6", "42"),
            "看相": ("hon3 soeng3", "44"),
            "自省": ("zi6 sing2", "29"),
            "解數": ("gaai2 sou3", "94"),
            "懷揣": ("waai4 caai1", "03"),
            "水磨": ("seoi2 mo6", "92"),
            "里長": ("lei5 zoeng2", "59"),
            "栗鈣土": ("leot6 koi3 tou2", "249"),
            "天呀": ("tin1 aa3", "34"),
            "吧嗒": ("baa1 taap3", "34"),
            "衣被": ("ji1 pei5", "35"),
            "被裝": ("pei5 zong1", "53"),
            "粘彈性": ("nim1 daan6 sing3", "324"),
            "著者": ("zyu3 ze2", "49"),
            "財長": ("coi4 zoeng2", "09"),
            "消耗量": ("siu1 hou3 loeng6", "342"),
            "朝綱": ("ciu4 gong1", "03"),
            "觀其行": ("gun1 kei4 hang6", "302"),
            "鮮見": ("sin2 gin3", "94"),
            "描畫": ("miu4 waak6", "02"),
            "重子": ("cung5 zi2", "59"),
            "閤家": ("hap6 gaa1", "23"),
            "同里": ("tung4 lei5", "05"),
            "徵辟": ("zing1 bik1", "33"),
            "報名表": ("bou3 ming4 biu2", "409"),
            "藏學": ("zong6 hok6", "22"),
            "創面": ("cong1 min6", "32"),
            "被覆": ("pei5 fuk1", "53"),
            "咯血": ("lok3 hyut3", "44"),
            "空行": ("hung1 hong4", "30"),
            "紅麴紅": ("hung4 guk1 hung4", "030"),
            "分櫱": ("fan1 jit6", "32"),
            "行政處分": ("hang4 zing3 cyu2 fan6", "0492"),
            "精神病院": ("zing1 san4 beng6 jyun2", "3029"),
            "瘋牛病": ("fung1 ngau4 beng6", "302"),
            "猜度": ("caai1 dok6", "32"),
            "降伏": ("hong4 fuk6", "02"),
            "乙方": ("jyut3 fong1", "43"),
            "計量學": ("gai3 loeng4 hok6", "402"),
            "頭面人物": ("tau4 min6 jan4 mat6", "0202"),
            "仔仔細細": ("zi2 zi2 sai3 sai3", "9944"),
            "種樹": ("zung3 syu6", "42"),
            "醜行": ("cau2 hang6", "92"),
            "鋪位": ("pou3 wai2", "49"),
            "吲哚": ("jan5 do2", "59"),
            "上解": ("soeng5 gaai3", "54"),
            "花呢": ("faa1 nei4", "30"),
            "行草": ("hang4 cou2", "09"),
            "行號": ("hong4 hou6", "02"),
            "自傳體": ("zi6 zyun6 tai2", "229"),
            "盛飯": ("sing4 faan6", "02"),
            "強迫性": ("koeng5 bik1 sing3", "534"),
            "挨鬥": ("ngaai4 dau3", "04"),
            "相面": ("soeng3 min6", "42"),
            "划手": ("waa4 sau2", "09"),
            "電話網": ("din6 waa6 mong5", "225"),
            "份數": ("fan6 sou3", "24"),
            "恬淡": ("tim4 daam6", "02"),
            "捻子": ("nin2 zi2", "99"),
            "病死率": ("beng6 sei2 leot6", "292"),
            "病毒感染者": ("beng6 duk6 gam2 jim5 ze2", "22959"),
            "蘊藉": ("wan3 ze3", "44"),
            "重活": ("cung5 wut6", "52"),
            "霜黴病": ("soeng1 mei4 beng6", "302"),
            "寒暑假": ("hon4 syu2 gaa3", "094"),
            "行間": ("hong4 gaan1", "03"),
            "錠子": ("ding6 zi2", "29"),
            "咿咿呀呀": ("ji1 ji1 aa1 aa1", "3333"),
            "拂面": ("fat1 min6", "32"),
            "積累率": ("zik1 leoi5 leot6", "352"),
            "喘吁吁": ("cyun2 heoi1 heoi1", "933"),
            "虎賁": ("fu2 ban1", "93"),
            "佚文": ("jat6 man4", "20"),
            "呢喃": ("nei4 naam4", "00"),
            "嫋娜": ("niu5 no5", "55"),
            "水泊": ("seoi2 bok6", "92"),
            "胼胝": ("pin4 zi1", "03"),
            "蛛網膜": ("zyu1 mong5 mok6", "352"),
            "規劃署": ("kwai1 waak6 cyu5", "325"),
            "打擊樂": ("daa2 gik1 ngok6", "932"),
            "執行長": ("zap1 hang4 zoeng2", "309"),
            "彈塑性": ("daan6 sou3 sing3", "244"),
            "機械系": ("gei1 haai6 hai6", "322"),
            "草莽英雄": ("cou2 mong5 jing1 hung4", "9530"),
            "長上": ("zoeng2 soeng6", "92"),
            "上座部": ("soeng6 zo6 bou6", "222"),
            "干擾機": ("gon1 jiu2 gei1", "393"),
            "種花": ("zung3 faa1", "43"),
            "復發率": ("fuk6 faat3 leot6", "242"),
            "雜著": ("zaap6 zyu3", "24"),
            "斗式": ("dau2 sik1", "93"),
            "相率": ("soeng1 seot1", "33"),
            "經幢": ("ging1 cong4", "30"),
            "傳主": ("zyun6 zyu2", "29"),
            "處理速度": ("cyu2 lei5 cuk1 dou6", "9532"),
            "件數": ("gin2 sou3", "94"),
            "分散相": ("fan1 saan3 soeng3", "344"),
            "抹香鯨": ("mut3 hoeng1 king4", "430"),
            "校樣": ("gaau3 joeng6", "42"),
            "住宅樓": ("zyu6 zaak6 lau4", "220"),
            "簡併": ("gaan2 bing6", "92"),
            "筆墨紙硯": ("bat1 mak6 zi2 jin6", "3292"),
            "締合": ("dai3 hap6", "42"),
            "閼氏": ("jin1 zi1", "33"),
            "霧滴": ("mou6 dik1", "23"),
            "電話局": ("din6 waa6 guk6", "222"),
            "校準": ("gaau3 zeon2", "49"),
            "樂句": ("ngok6 geoi3", "24"),
            "標識符": ("biu1 zi3 fu4", "340"),
            "甩頭": ("seot1 tau4", "30"),
            "石磙": ("sek6 gwan2", "29"),
            "紅燈籠": ("hung4 dang1 lung4", "030"),
            "著譯": ("zyu3 jik6", "42"),
            "間雜": ("gaan3 zaap6", "42"),
            "闇弱": ("am3 joek6", "42"),
            "漂漂亮亮": ("piu3 piu3 loeng6 loeng6", "4422"),
            "行款": ("hong4 fun2", "09"),
            "調相": ("tiu4 soeng3", "04"),
            "紀行": ("gei3 hang4", "40"),
        }
        candidates = ingest_lexicon_json(CURATED, source_id="curated")
        pairs = {(row.char, row.jyutping, row.code) for row in candidates}
        batch = [row for row in json.loads(CURATED.read_text(encoding="utf-8")) if row.get("batch") in {BATCH, BATCH_02, BATCH_03, BATCH_04, BATCH_05, BATCH_06, BATCH_07, BATCH_08, BATCH_09, BATCH_10}]
        self.assertTrue({(to_traditional(row["char"]), row["jyutping"], row["code"]) for row in batch}.issubset(pairs))
        engine = create_engine("sqlite:///:memory:")
        reset_word_cache_for_tests()
        try:
            Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
            with Session(engine) as db:
                persist_lexicon_candidates(db, candidates)
                db.commit()
                for literal, (jyutping, code) in cases.items():
                    self.assertTrue((to_traditional(literal), jyutping, code) in pairs, literal)
                    for mode in ("m1", "m2", "m3"):
                        with self.subTest(literal=literal, mode=mode):
                            result = QueryEngine().execute(SearchContext(code, None, None, mode, 5000, 0, db))
                            self.assertIn(to_traditional(literal), {row["char"] for row in result.items})
                for literal, wrong_code in (("這種", "99"), ("行長", "00"), ("利潤率", "229"), ("年老多病", "0533"), ("太重", "42"), ("轉入", "42"), ("消費量", "340"), ("上表", "29"), ("重劍", "24"), ("相中", "33"), ("相中", "44"), ("糖分", "03"), ("生長期", "300"), ("藏醫", "03"), ("陀螺儀", "090"), ("醜行", "90"), ("自傳體", "299"), ("電話網", "295"), ("划手", "29"), ("花呢", "33"), ("上解", "59"), ("份數", "29")):
                    with self.subTest(literal=literal, wrong_code=wrong_code):
                        result = QueryEngine().execute(SearchContext(wrong_code, None, None, "m3", 1000, 0, db))
                        self.assertNotIn(to_traditional(literal), {row["char"] for row in result.items})
        finally:
            reset_word_cache_for_tests()
            engine.dispose()

    def test_fifth_batch_is_reviewed_and_keeps_all_previous_rows(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_05}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_05}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(input_fingerprint(curated, meta, 5), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_05]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        self.assertNotIn("defer", {row["verdict"] for row in review})
        self.assertTrue({"法意", "氆氌", "艇長", "形相", "槓子", "步行者"}.issubset({row["char"] for row in batch}))

    def test_sixth_batch_keeps_previous_rows_and_only_promotes_reviewed_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_06}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_06}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 6), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_06]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        self.assertNotIn("defer", {row["verdict"] for row in review})
        self.assertTrue({"里長", "栗鈣土", "椰乾", "石製", "臨場發揮", "解數", "吧嗒"}.issubset({row["char"] for row in batch}))
        self.assertTrue({row["char"] for row in batch}.isdisjoint({"自貢", "北師大", "本草綱目", "哥倆", "扒拉", "蒸饃"}))

    def test_seventh_batch_preserves_previous_rows_and_holds_uncertain_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_07}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_07}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 7), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_07]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(accepted, {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        self.assertEqual({row["char"] for row in review if row["verdict"] == "defer"}, {"滴噠"})
        self.assertTrue({row["char"] for row in batch}.isdisjoint({"滴噠", "臊子", "夠戧", "報名錶", "徵闢", "同裏"}))
        for row in batch:
            self.assertEqual(to_traditional(row["char"]), to_traditional(to_traditional(row["char"])))

    def test_eighth_batch_preserves_previous_source_and_excludes_unresolved_drafts(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_08}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_08}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 8), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_08]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(accepted, {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        deferred = {"散碎", "散打", "噼噼啪啪", "噼裏啪啦", "噼啪"}
        self.assertEqual({row["char"] for row in review if row["verdict"] == "defer"}, deferred)
        self.assertTrue({row["char"] for row in batch}.isdisjoint(deferred | {"兔崽子", "亭子間", "頭麪人物", "劃手", "首髮式"}))
        for row in batch:
            self.assertEqual(to_traditional(row["char"]), to_traditional(to_traditional(row["char"])))

    def test_ninth_batch_preserves_previous_source_and_records_exact_old_reading_repairs(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_09}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_09}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 9), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_09]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(accepted, {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        self.assertEqual({row["char"] for row in review if row["verdict"] == "defer"}, {"行風", "咪咪"})
        self.assertTrue({row["char"] for row in batch}.isdisjoint({"行風", "咪咪", "哥兒們", "腦瓜子", "幹擾機", "機械繫", "鬥式", "複發率"}))
        for row in batch:
            self.assertEqual(to_traditional(row["char"]), to_traditional(to_traditional(row["char"])))
        path = REVIEW.parent / meta["existing_reading_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_reading_review_sha256"])
        repairs = review_rows(path)
        self.assertEqual(len(repairs), meta["existing_source_reading_repairs"])
        candidates = []
        for row in repairs:
            self.assertIn("mong4", row["previous_jyutping"].split())
            self.assertEqual(row["jyutping"], row["previous_jyutping"].replace("mong4", "mong5"))
            candidates.append(LexiconCandidate(row["char"], row["previous_jyutping"], row["previous_code"], ("kaifang",)))
            if row["action"] == "delete":
                candidates.append(LexiconCandidate(row["char"], row["jyutping"], row["code"], ("rime_words",)))
        candidates.append(LexiconCandidate("莽", "mong6", "2", ("rime",)))
        fixed = apply_lexicon_overlay(candidates, load_corrections())
        expected = {(row["char"], row["jyutping"], row["code"]) for row in repairs} | {("莽", "mong6", "2")}
        self.assertEqual({(row.char, row.jyutping, row.code) for row in fixed}, expected)
        self.assertEqual(len(fixed), len(expected))

    def test_tenth_batch_preserves_prior_rows_and_defers_unresolved_sound_words(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_10}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_10}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 10), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_10]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(accepted, {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        self.assertEqual({row["char"] for row in review if row["verdict"] == "defer"}, {"咯吱咯吱"})
        self.assertTrue({row["char"] for row in batch}.isdisjoint({"咯吱咯吱", "腦袋瓜子", "裝孫子", "明兒個", "金鋼", "煩燥", "複員軍人"}))
        for row in batch:
            self.assertEqual(to_traditional(row["char"]), to_traditional(to_traditional(row["char"])))

    def test_gold_and_stone_repair_does_not_change_capacity_unit_readings(self):
        meta = json.loads((REVIEW.parent / f"{BATCH_06}.meta.json").read_text(encoding="utf-8"))
        path = REVIEW.parent / meta["existing_reading_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_reading_review_sha256"])
        review = review_rows(path)
        self.assertEqual(len(review), meta["existing_source_reading_repairs"])
        original = LexiconCandidate("金石", "gam1 daam3", "34", ("rime",))
        capacity = LexiconCandidate("一石", "jat1 daam3", "34", ("fixture",))
        fixed = apply_lexicon_overlay([original, capacity], load_corrections())
        self.assertEqual([(r.char, r.jyutping, r.code) for r in fixed], [("金石", "gam1 sek6", "32"), ("一石", "jat1 daam3", "34")])
        self.assertEqual(fixed[0].sources, original.sources)


if __name__ == "__main__":
    unittest.main()
