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
BATCH_11 = "2026-11-06-written-b11"
BATCH_12 = "2026-11-06-written-b12"
BATCH_13 = "2026-11-06-written-b13"
BATCH_14 = "2026-11-06-written-b14"


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
            "白面书生": "白面書生", "白面書生": "白面書生", "白麪書生": "白面書生",
            "斗门": "斗門", "斗門": "斗門", "鬥門": "斗門",
            "车斗": "車斗", "車斗": "車斗", "車鬥": "車斗",
            "家具城": "家具城", "傢俱城": "家具城",
            "征南将军": "征南將軍", "征南將軍": "征南將軍", "徵南將軍": "征南將軍",
            "干扰源": "干擾源", "干擾源": "干擾源", "幹擾源": "干擾源",
            "条几": "條几", "條几": "條几", "條幾": "條几",
            "抗干扰性": "抗干擾性", "抗干擾性": "抗干擾性", "抗幹擾性": "抗干擾性",
            "能征惯战": "能征慣戰", "能征慣戰": "能征慣戰", "能徵慣戰": "能征慣戰",
            "毒血症": "毒血症", "毒血癥": "毒血症",
            "仪表板": "儀表板", "儀表板": "儀表板", "儀錶板": "儀表板",
            "记里鼓车": "記里鼓車", "記里鼓車": "記里鼓車", "記裏鼓車": "記里鼓車",
            "数斗": "數斗", "數斗": "數斗", "數鬥": "數斗",
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                self.assertEqual(to_traditional(original), expected)
                self.assertEqual(to_traditional(expected), expected)
        for unchanged in ("幹部", "干支", "徵求", "象徵", "鬥爭", "幾何", "醜態", "洋麵", "鬱鬱", "憂鬱", "這裏", "闢謠", "手錶", "麪粉", "劃分", "劃界", "繫帶", "幹事", "鬥牛", "白麪", "白麪包", "車鬥士", "鬥門之戰"):
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
            "令妹": ("ling6 mui2", "29"),
            "朝聖者": ("ciu4 sing3 ze2", "049"),
            "外行星": ("ngoi6 hang4 sing1", "203"),
            "尊師重教": ("zyun1 si1 zung6 gaau3", "3324"),
            "行狀": ("hang6 zong6", "22"),
            "賁門": ("ban1 mun4", "30"),
            "計量經濟學": ("gai3 loeng4 ging1 zai3 hok6", "40342"),
            "鑑相器": ("gaam3 soeng3 hei3", "444"),
            "協處理器": ("hip3 cyu2 lei5 hei3", "4954"),
            "位錯": ("wai2 co3", "94"),
            "斷層湖": ("dyun6 cang4 wu4", "200"),
            "溜掉": ("liu1 diu6", "32"),
            "畫符": ("waak6 fu4", "20"),
            "葡萄膜": ("pou4 tou4 mok6", "002"),
            "談興": ("taam4 hing3", "04"),
            "複擺": ("fuk1 baai2", "39"),
            "斗門": ("dau2 mun4", "90"),
            "車斗": ("ce1 dau2", "39"),
            "主簿": ("zyu2 bou6", "92"),
            "創痛": ("cong1 tung3", "34"),
            "嫋嫋娜娜": ("niu5 niu5 no5 no5", "5555"),
            "繾綣": ("hin2 hyun2", "99"),
            "處理事件": ("cyu2 lei5 si6 gin2", "9529"),
            "胎膜": ("toi1 mok6", "32"),
            "征南將軍": ("zing1 naam4 zoeng1 gwan1", "3033"),
            "干擾源": ("gon1 jiu2 jyun4", "390"),
            "鼻黏膜": ("bei6 nim4 mok6", "202"),
            "種豆得豆": ("zung3 dau6 dak1 dau6", "4232"),
            "會員卡": ("wui6 jyun4 kaa1", "203"),
            "清創": ("cing1 cong1", "33"),
            "櫟樹": ("lik1 syu6", "32"),
            "根冠": ("gan1 gun1", "33"),
            "朝覲者": ("ciu4 gan6 ze2", "029"),
            "冬雪": ("dung1 syut3", "34"),
            "秋水仙鹼": ("cau1 seoi2 sin1 gaan2", "3939"),
            "生命史": ("sang1 ming6 si2", "329"),
            "詩行": ("si1 hong4", "30"),
            "複合肥": ("fuk1 hap6 fei4", "320"),
            "展弦比": ("zin2 jin4 bei2", "909"),
            "藏戲": ("zong6 hei3", "24"),
            "黑色素瘤": ("hak1 sik1 sou3 lau4", "3340"),
            "沖頭": ("cung1 tau4", "30"),
            "沖壓件": ("cung1 aat3 gin6", "342"),
            "熨帖": ("wat1 tip3", "34"),
            "睫毛膏": ("zit6 mou4 gou1", "203"),
            "縱橫交織": ("zung1 waang4 gaau1 zik1", "3033"),
            "個位數": ("go3 wai2 sou3", "494"),
            "分支行": ("fan1 zi1 hong4", "330"),
            "舞蹈病": ("mou5 dou6 beng6", "522"),
            "記里鼓車": ("gei3 lei5 gu2 ce1", "4593"),
            "數斗": ("sou3 dau2", "49"),
            "草長鶯飛": ("cou2 zoeng2 ang1 fei1", "9933"),
            "臧否人物": ("zong1 pei2 jan4 mat6", "3902"),
            "詩思": ("si1 si3", "34"),
            "茄克": ("gaa1 hak1", "33"),
            "創鉅痛深": ("cong1 geoi6 tung3 sam1", "3243"),
            "曳光": ("jai6 gwong1", "23"),
            "聾啞學校": ("lung4 aa2 hok6 haau6", "0922"),
            "山參": ("saan1 sam1", "33"),
        }
        candidates = ingest_lexicon_json(CURATED, source_id="curated")
        pairs = {(row.char, row.jyutping, row.code) for row in candidates}
        batch = [row for row in json.loads(CURATED.read_text(encoding="utf-8")) if row.get("batch") in {BATCH, BATCH_02, BATCH_03, BATCH_04, BATCH_05, BATCH_06, BATCH_07, BATCH_08, BATCH_09, BATCH_10, BATCH_11, BATCH_12, BATCH_13, BATCH_14}]
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

    def test_eleventh_batch_keeps_prior_rows_and_records_exact_literal_migration(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_11}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_11}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 11), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_11]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(accepted, {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        deferred = {"劈劈啪啪", "忽喇喇", "撲稜稜"}
        self.assertEqual({row["char"] for row in review if row["verdict"] == "defer"}, deferred)
        self.assertTrue({row["char"] for row in batch}.isdisjoint(deferred | {"爺兒們", "撂挑子", "小崽子", "主薄", "往複式", "復擺", "鬥門", "車鬥"}))
        for row in batch:
            self.assertEqual(to_traditional(row["char"]), to_traditional(to_traditional(row["char"])))
        path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        migration = review_rows(path)
        self.assertEqual(len(migration), meta["existing_literal_migrations"])
        self.assertEqual([(r["previous_char"], r["char"], r["jyutping"], r["code"]) for r in migration], [("白麪書生", "白面書生", "baak6 min6 syu1 sang1", "2233")])
        self.assertEqual(to_traditional(migration[0]["previous_char"]), migration[0]["char"])

    def test_twelfth_batch_preserves_prior_rows_and_separates_word_senses(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_12}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_12}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 12), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_12]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        deferred = {"哼哼哈哈", "哐當", "啊呀呀"}
        self.assertEqual({row["char"] for row in review if row["verdict"] == "defer"}, deferred)
        self.assertTrue({row["char"] for row in batch}.isdisjoint(deferred | {"腳脖子", "土坷垃", "屁股蛋子", "手腕子", "幹仗", "石藥集團"}))
        self.assertIn("禁製品", {row["char"] for row in batch})
        self.assertEqual(meta["existing_literal_migrations"], 0)
        for row in batch:
            self.assertEqual(to_traditional(row["char"]), to_traditional(to_traditional(row["char"])))
        for original in ("幹擾源頭", "徵南將軍府"):
            self.assertEqual(to_traditional(original), original)

    def test_thirteenth_batch_records_chung_repair_and_contextual_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_13}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_13}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({row["id"].split(":")[0] for row in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 13), meta["input_curated_sha256"])
        batch = [row for row in curated if row.get("batch") == BATCH_13]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in review if row["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
        repairs = [row for row in review if row["verdict"] == "repair"]
        self.assertEqual([(r["char"], r["previous_jyutping"], r["jyutping"], r["code"]) for r in repairs], [("沖頭", "cung3 tau4", "cung1 tau4", "30")])
        self.assertEqual(len(repairs), meta["reading_repairs"])
        triples = {(r["char"], r["jyutping"], r["code"]) for r in curated}
        self.assertIn(("沖頭", "cung1 tau4", "30"), triples)
        self.assertNotIn(("沖頭", "cung3 tau4", "40"), triples)
        deferred = {"呱噠", "咕嘟嘟"}
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, deferred)
        self.assertTrue({r["char"] for r in batch}.isdisjoint(deferred | {"莊戶人", "賊亮", "貓腰", "胡茬", "苞谷", "脆生生", "端掉", "矬子"}))
        self.assertEqual(meta["existing_literal_migrations"], 0)
        for original in ("幹部", "徵求", "鬥爭", "抗幹擾性能", "能徵慣戰者", "儀錶", "幾何", "癥結"):
            self.assertEqual(to_traditional(original), original)

    def test_fourteenth_batch_preserves_prior_source_and_keeps_written_mandarin(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_14}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_14}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({r["id"].split(":")[0] for r in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 14), meta["input_curated_sha256"])
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["existing_literal_migrations"], 0)
        batch = [r for r in curated if r.get("batch") == BATCH_14]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"}
        self.assertEqual(apply_recorded_repairs(accepted), {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        deferred = {"吱吱嘎嘎", "嘁嘁嚓嚓", "嘎啦"}
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, deferred)
        literals = {r["char"] for r in batch}
        self.assertTrue({"吃住行", "包吃", "血豆腐", "羊雜碎", "似水流年", "好生生", "臧否人物"}.issubset(literals))
        self.assertTrue(literals.isdisjoint(deferred | {"大老爺們", "姐兒們", "縮脖子", "駕駛本", "窟窿眼", "藥罐子"}))
        pairs = {(r["char"], r["jyutping"]) for r in curated}
        for wrong in [("茄克", "ke2 hak1"), ("草長鶯飛", "cou2 coeng4 ang1 fei1"),
                      ("臧否人物", "zong1 fau2 jan4 mat6"), ("詩思", "si1 si1"),
                      ("曳光", "jai5 gwong1"), ("山參", "saan1 caam1"),
                      ("嵌合體", "tham3 hap6 tai2")]:
            self.assertNotIn(wrong, pairs)
        for original in ("幹部", "鬥爭", "記裏鼓車圖", "數鬥之後"):
            self.assertEqual(to_traditional(original), original)

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
