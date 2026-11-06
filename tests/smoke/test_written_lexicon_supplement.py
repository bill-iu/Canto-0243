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
from app.lexicon.word_usage import load_word_usage
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
BATCH_15 = "2026-11-06-written-b15"
BATCH_16 = "2026-11-06-written-b16"
BATCH_17 = "2026-11-06-written-b17"
BATCH_18 = "2026-11-06-written-b18"
BATCH_19 = "2026-11-06-written-b19"
BATCH_20 = "2026-11-06-written-b20"
BATCH_21 = "2026-11-06-written-b21"
BATCH_22 = "2026-11-06-written-b22"
BATCH_23 = "2026-11-06-written-b23"
BATCH_24 = "2026-11-06-written-b24"
BATCH_25 = "2026-11-06-written-b25"
BATCH_26 = "2026-11-06-written-b26"
BATCH_27 = "2026-11-06-written-b27"
BATCH_28 = "2026-11-06-written-b28"
BATCH_29 = "2026-11-06-written-b29"
BATCH_30 = "2026-11-06-written-b30"
BATCH_31 = "2026-11-06-written-b31"
BATCH_32 = "2026-11-06-written-b32"
BATCH_33 = "2026-11-06-written-b33"
BATCH_34 = "2026-11-06-written-b34"
BATCH_35 = "2026-11-06-written-b35"
BATCH_36 = "2026-11-06-written-b36"
BATCH_37 = "2026-11-06-written-b37"
BATCH_38 = "2026-11-06-written-b38"
BATCH_39 = "2026-11-06-written-b39"
BATCH_40 = "2026-11-06-written-b40"
BATCH_41 = "2026-11-06-written-b41"
BATCH_42 = "2026-11-06-written-b42"
BATCH_43 = "2026-11-06-written-b43"


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
            "风斗": "風斗", "風斗": "風斗", "風鬥": "風斗",
            "划得来": "划得來", "划得來": "划得來", "劃得來": "划得來",
            "医托": "醫托", "醫托": "醫托", "醫託": "醫托",
            "无精打采": "無精打采", "無精打採": "無精打采",
            "离题万里": "離題萬里", "離題萬裏": "離題萬里",
            "前程万里": "前程萬里", "前程萬裏": "前程萬里",
            "基托": "基托", "基託": "基托",
            "斗車": "斗車", "斗车": "斗車", "鬥車": "鬥車",
            "日进斗金": "日進斗金", "日進鬥金": "日進斗金",
            "星移斗转": "星移斗轉", "星移鬥轉": "星移斗轉",
            "没精打采": "沒精打采", "沒精打採": "沒精打采",
            "烘云托月": "烘雲托月", "烘雲託月": "烘雲托月",
            "鄉愿": "鄉愿", "鄉願": "鄉愿",
            "锥栗": "錐栗", "錐慄": "錐栗",
            "铲斗": "剷斗", "剷鬥": "剷斗",
            "抓斗": "抓斗", "抓鬥": "抓斗",
            "翻斗": "翻斗", "翻鬥": "翻斗",
            "开伙": "開伙", "開伙": "開伙", "開夥": "開伙",
            "干扰能力": "干擾能力", "幹擾能力": "干擾能力",
            "有征无战": "有征無戰", "有徵無戰": "有征無戰",
            "并条机": "併條機", "並條機": "併條機", "併條機": "併條機",
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
            "心情愉快": ("sam1 cing4 jyu4 faai3", "3004"),
            "忍受着": ("jan2 sau6 zoek6", "922"),
            "性交易": ("sing3 gaau1 jik6", "432"),
            "悲咽": ("bei1 jit3", "34"),
            "情見於色": ("cing4 jin6 jyu1 sik1", "0233"),
            "這種": ("ze5 zung2", "59"),
            "佚事": ("jat6 si6", "22"),
            "成分表": ("sing4 fan6 biu2", "029"),
            "鶉衣百結": ("seon4 ji1 baak3 git3", "0344"),
            "嫵媚多姿": ("mou5 mei6 do1 zi1", "5233"),
            "心宿": ("sam1 sau3", "34"),
            "一盎司": ("jat1 on1 si1", "333"),
            "干擾能力": ("gon1 jiu2 nang4 lik6", "3902"),
            "併條機": ("bing3 tiu4 gei1", "403"),
            "搖搖曳曳": ("jiu4 jiu4 jai6 jai6", "0022"),
            "醫專": ("ji1 zyun1", "33"),
            "青少年宮": ("cing1 siu3 nin4 gung1", "3403"),
            "說謊者": ("syut3 fong1 ze2", "439"),
            "豪商巨賈": ("hou4 soeng1 geoi6 gu2", "0329"),
            "浮點數": ("fau4 dim2 sou3", "094"),
            "重病纏身": ("zung6 beng6 cin4 san1", "2203"),
            "抓斗": ("zaau2 dau2", "99"),
            "翻斗": ("faan1 dau2", "39"),
            "壓卷之作": ("aat3 gyun3 zi1 zok3", "4434"),
            "飛簷翹角": ("fei1 sim4 kiu4 gok3", "3004"),
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
            "一瀉萬里": ("jat1 se3 maan6 lei5", "3425"),
            "一夔一契": ("jat1 kwai4 jat1 sit3", "3034"),
            "一字不易": ("jat1 zi6 bat1 jik6", "3232"),
            "一筆一畫": ("jat1 bat1 jat1 waak6", "3332"),
            "轎廂": ("giu6 soeng1", "23"),
            "計量局": ("gai3 loeng4 guk6", "402"),
            "新加坡人": ("san1 gaa3 bo1 jan4", "3430"),
            "人為財死": ("jan4 wai6 coi4 sei2", "0209"),
            "人人為我": ("jan4 jan4 wai6 ngo5", "0025"),
            "人涉卬否": ("jan4 sip3 ngong4 fau2", "0409"),
            "予取予奪": ("jyu4 ceoi2 jyu4 dyut6", "0902"),
            "乘肥衣輕": ("sing4 fei4 ji3 hing1", "0043"),
            "主骨架": ("zyu2 gwat1 gaa3", "934"),
        }
        candidates = ingest_lexicon_json(CURATED, source_id="curated")
        pairs = {(row.char, row.jyutping, row.code) for row in candidates}
        batch = [row for row in json.loads(CURATED.read_text(encoding="utf-8")) if row.get("batch") in {BATCH, BATCH_02, BATCH_03, BATCH_04, BATCH_05, BATCH_06, BATCH_07, BATCH_08, BATCH_09, BATCH_10, BATCH_11, BATCH_12, BATCH_13, BATCH_14, BATCH_15, BATCH_16, BATCH_17, BATCH_18, BATCH_19, BATCH_20, BATCH_21, BATCH_22, BATCH_23, BATCH_24, BATCH_25, BATCH_26, BATCH_27, BATCH_28, BATCH_29, BATCH_30, BATCH_31, BATCH_32, BATCH_33, BATCH_34, BATCH_35, BATCH_36, BATCH_37, BATCH_38, BATCH_39, BATCH_40, BATCH_41, BATCH_42, BATCH_43}]
        usage = load_word_usage(CURATED.with_name("word_usage.tsv"))
        withdrawn = {literal for literal, grade in usage.items() if grade.withdraw_curated}
        self.assertTrue({(to_traditional(row["char"]), row["jyutping"], row["code"]) for row in batch if to_traditional(row["char"]) not in withdrawn}.issubset(pairs))
        self.assertTrue(withdrawn.isdisjoint({row.char for row in candidates}))
        engine = create_engine("sqlite:///:memory:")
        reset_word_cache_for_tests()
        try:
            Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
            with Session(engine) as db:
                persist_lexicon_candidates(db, candidates)
                db.commit()
                for literal, (jyutping, code) in cases.items():
                    if to_traditional(literal) in withdrawn:
                        self.assertNotIn((to_traditional(literal), jyutping, code), pairs)
                        continue
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
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
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

    def test_fifteenth_batch_retains_context_readings_and_exact_normalization(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_15}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_15}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({r["id"].split(":")[0] for r in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 15), meta["input_curated_sha256"])
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["existing_literal_migrations"], 0)
        batch = [r for r in curated if r.get("batch") == BATCH_15]
        self.assertEqual(len(batch), meta["added_rows"])
        accepted = {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"}
        self.assertEqual(accepted, {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        deferred = {"呀呀", "懵裏懵懂"}
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, deferred)
        literals = {r["char"] for r in batch}
        self.assertTrue({"風斗", "划得來", "醫托", "不疼不癢", "皮夾子", "朝乾夕惕", "隨風而逝", "風華絕代"}.issubset(literals))
        self.assertTrue(literals.isdisjoint(deferred | {"豆腐腦", "奶皮子", "爺倆", "抹不開", "冰碴"}))
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for wrong in [("朝乾夕惕", "ziu1 gon1 zik6 tik1"), ("綸巾羽扇", "leon4 gan1 jyu5 sin3"),
                      ("柞絲綢", "zaa3 si1 cau4"), ("擬題", "ji4 tai4"),
                      ("並行工程", "bing6 hong6 gung1 cing4"), ("臧否", "zong1 fau2"),
                      ("分子病", "fan6 zi2 beng6"), ("苯醚", "bun2 mei4")]:
            self.assertNotIn(wrong, pairs)
        for original in ("鬥爭", "劃分", "委託", "風鬥之戰", "劃得來者", "醫託之言"):
            self.assertEqual(to_traditional(original), original)

    def test_sixteenth_batch_preserves_prior_grades_and_records_literal_migrations(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_16}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_16}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({r["id"].split(":")[0] for r in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 16), meta["input_curated_sha256"])
        self.assertEqual(meta["reading_repairs"], 0)
        batch = [r for r in curated if r.get("batch") == BATCH_16]
        accepted = {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"}
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual(accepted, {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertEqual({r["char"] for r in review if r["previous_verdict"] == "reject" and r["verdict"] == "accept"}, {"大兒媳", "孩子王", "舅子"})
        self.assertEqual(sum(r["verdict"] == "defer" for r in review), 11)
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"刺兒頭", "尥蹶子", "老鼻子", "刀子嘴", "胰子"}))
        path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        migrations = review_rows(path)
        self.assertEqual(len(migrations), meta["existing_literal_migrations"])
        self.assertEqual({(r["previous_char"], r["char"]) for r in migrations}, {("無精打採", "無精打采"), ("前程萬裏", "前程萬里")})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for wrong in [("創痕", "cong3 han4"), ("夜靜更深", "je6 zing6 gang3 sam1"),
                      ("勘察隊", "tham3 caat3 deoi6"), ("鴨肫", "aap3 seon4"),
                      ("茜素", "sai1 sou3"), ("轉隸", "zyun3 dai6"),
                      ("重點班", "cung5 dim2 baan1"), ("靜電荷", "zing6 din6 ho4")]:
            self.assertNotIn(wrong, pairs)
        for original in ("委託", "採集", "這裏", "前程萬裏圖", "基託之言"):
            self.assertEqual(to_traditional(original), original)

    def test_seventeenth_batch_retains_complete_phrases_and_separates_cart_senses(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_17}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_17}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({r["id"].split(":")[0] for r in review}), meta["review_candidate_ids"])
        self.assertEqual(input_fingerprint(curated, meta, 17), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_17]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"譁嘩啦啦"})
        revisited = {"一人得道", "只怕有心人", "凡事預則立", "不謀其政", "上有政策", "下有對策", "落花有意", "耳聽為虛", "精誠所至"}
        self.assertEqual({r["char"] for r in review if r["previous_verdict"] == "reject" and r["verdict"] == "accept"}, revisited)
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for wrong in [("毛呢", "mou4 ne1"), ("焊縫", "hon2 fung4"), ("自作主張", "zi6 zou6 zyu2 zoeng1"),
                      ("遇難成祥", "jyu6 naan6 cing4 coeng4"), ("松柴", "sung4 caai4"),
                      ("期冀", "kei4 gei3"), ("便宜從事", "pin4 ji4 cung4 si6"), ("斗車", "dau3 ce1")]:
            self.assertNotIn(wrong, pairs)
        self.assertIn(("斗車", "dau2 ce1"), pairs)
        path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        migrations = review_rows(path)
        self.assertEqual(len(migrations), meta["existing_literal_migrations"])
        self.assertEqual({r["previous_char"] for r in migrations}, {"星移鬥轉", "沒精打採", "烘雲託月", "鄉願"})
        for original in ("鬥車", "鬥爭", "委託", "意願", "錐慄之言", "剷鬥之戰"):
            self.assertEqual(to_traditional(original), original)

    def test_eighteenth_batch_preserves_contextual_readings_and_cooking_literal(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_18}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_18}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({r["id"].split(":")[0] for r in review}), meta["review_candidate_ids"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(input_fingerprint(curated, meta, 18), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_18]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"怪里怪氣", "粘糊糊"})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        self.assertTrue({("止疼藥", "zi2 tang4 joek6"), ("氧化鈷", "joeng5 faa3 gu1"),
                         ("缺省", "kyut3 saang2"), ("踢毽", "tek3 jin2"),
                         ("重病纏身", "cung5 beng6 cin4 san1"), ("陶塤", "tou4 fan1"),
                         ("靜如處子", "zing6 jyu4 cyu2 zi2")}.issubset(pairs))
        for wrong in [("噬人鯊", "sai4 jan4 saa1"), ("豪商巨賈", "hou4 soeng1 geoi6 gaa2"),
                      ("浮點數", "fau4 dim2 sou2"), ("審校", "sam2 haau6"),
                      ("枳殼", "zat1 hok6"), ("藏學家", "cong4 hok6 gaa1"),
                      ("重病纏身", "zung6 bing6 cin4 san1")]:
            self.assertNotIn(wrong, pairs)
        path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        migrations = review_rows(path)
        self.assertEqual(len(migrations), meta["existing_literal_migrations"])
        self.assertEqual({(r["previous_char"], r["char"]) for r in migrations}, {("開夥", "開伙")})
        for original in ("鬥車", "鬥爭", "同夥", "開夥爨", "抓鬥之戰", "翻鬥之戰"):
            self.assertEqual(to_traditional(original), original)

    def test_nineteenth_batch_revisits_generic_expressions_and_retains_valid_variants(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_19}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_19}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(len({r["id"].split(":")[0] for r in review}), meta["review_candidate_ids"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(input_fingerprint(curated, meta, 19), meta["input_curated_sha256"])
        repairs = [r for r in review if r["verdict"] == "repair"]
        self.assertEqual(meta["reading_repairs"], 1)
        self.assertEqual([(r["char"], r["previous_jyutping"], r["jyutping"], r["code"]) for r in repairs],
                         [("相冊", "soeng1 caak3", "soeng2 caak3", "94")])
        self.assertNotIn(("相冊", "soeng1 caak3"), {(r["char"], r["jyutping"]) for r in curated})
        batch = [r for r in curated if r.get("batch") == BATCH_19]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        revisited = {"醫專", "青少年宮", "說謊者", "跟隨者", "違規者", "討債人", "負債人", "進攻方"}
        self.assertEqual({r["char"] for r in review if r["previous_verdict"] == "reject" and r["verdict"] == "accept"}, revisited)
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"},
                         {"鹼面", "丁丁冬冬", "半掩門", "叭嗒", "咔噠", "咯吱吱", "啪嚓", "嘀嘀", "生壺"})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        self.assertTrue({("簷瓦", "jam4 ngaa5"), ("心宿", "sam1 suk1"),
                         ("滑天下之大稽", "waat6 tin1 haa6 zi1 daai6 kai1"),
                         ("彈簧機", "daan6 wong4 gei1"), ("強姦民意", "koeng4 gaan1 man4 ji3")}.issubset(pairs))
        for wrong in [("佚事", "dit6 si6"), ("一盎司", "jat1 on1 si2"),
                      ("嫵媚多姿", "mou4 mei4 do1 zi1"), ("搖搖曳曳", "jiu4 jiu2 jai1 jai1"),
                      ("干擾能力", "gon3 jiu2 nang4 lik6"), ("派出所長", "paai3 ceot1 so2 coeng4"),
                      ("病毒檢測", "bing6 duk6 gim2 cak1")]:
            self.assertNotIn(wrong, pairs)
        path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        self.assertEqual({(r["previous_char"], r["char"]) for r in review_rows(path)}, {("有徵無戰", "有征無戰")})
        for original in ("徵求", "象徵", "幹部", "並且", "有徵無戰者", "並條機械"):
            self.assertEqual(to_traditional(original), original)

    def test_twentieth_batch_preserves_prior_rows_and_records_scope_revisits(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_20}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_20}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 100)
        self.assertEqual(input_fingerprint(curated, meta, 20), meta["input_curated_sha256"])
        self.assertEqual(meta["reading_repairs"], 0)
        batch = [r for r in curated if r.get("batch") == BATCH_20]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        restored = {r["char"] for r in review if r["previous_verdict"] == "reject" and r["verdict"] == "accept"}
        self.assertTrue({"同文館", "宮者", "護園人", "駕車人", "新加坡人", "計量局", "乾乾的", "一個腳印"}.issubset(restored))
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        self.assertTrue({("一簞食", "jat1 daan1 sik6"), ("一簞食", "jat1 daan1 zi6"),
                         ("轎廂", "giu6 soeng1"), ("轎廂", "kiu2 soeng1")}.issubset(pairs))
        self.assertNotIn(("轎廂", "kiu6 soeng1"), pairs)
        self.assertTrue({"一日三複", "一日三覆", "陽莖"}.issubset({r["char"] for r in review if r["verdict"] == "defer"}))
        for original, expected in [("遊離鈣", "游離鈣"), ("釜底遊魚", "釜底游魚"),
                                   ("一手託天", "一手托天"), ("一瀉萬裏", "一瀉萬里"), ("一舉萬裏", "一舉萬里")]:
            self.assertEqual(to_traditional(original), expected)
            self.assertEqual(to_traditional(expected), expected)
        for literal in ("遊玩", "寄託", "裏面", "一舉萬裏者"):
            self.assertEqual(to_traditional(literal), literal)

    def test_twenty_first_batch_records_context_repairs_and_preserves_valid_variants(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_21}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_21}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 3)
        self.assertEqual(input_fingerprint(curated, meta, 21), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_21]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        repairs = [r for r in review if r["verdict"] == "repair"]
        self.assertEqual([(r["char"], r["previous_jyutping"], r["jyutping"]) for r in repairs],
                         [("不可勝計", "bat1 ho2 sing3 gai3", "bat1 ho2 sing1 gai3")])
        pairs = {(r["char"], r["jyutping"]) for r in curated}
        self.assertIn(("不可勝計", "bat1 ho2 sing1 gai3"), pairs)
        self.assertNotIn(("不可勝計", "bat1 ho2 sing3 gai3"), pairs)
        for word, readings in [
            ("喜不自勝", ("hei2 bat1 zi6 sing3", "hei2 bat1 zi6 sing1")),
            ("丁腈橡膠", ("ding1 cing1 zoeng6 gaau1", "ding1 zing1 zoeng6 gaau1")),
            ("世風澆薄", ("sai3 fung1 hiu1 bok6", "sai3 fung1 giu1 bok6")),
            ("不分首從", ("bat1 fan1 sau2 cung4", "bat1 fan1 sau2 zung6")),
            ("上籃得分", ("soeng5 laam2 dak1 fan1", "soeng5 laam4 dak1 fan1")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs))
        self.assertTrue({"不自滿假", "世處", "並列蛋白"}.issubset({r["char"] for r in review if r["verdict"] == "defer"}))
        self.assertIn("瞧瞧", {r["char"] for r in review if r["previous_verdict"] == "reject" and r["verdict"] == "accept"})
        literal_path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(literal_path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        self.assertEqual({(r["previous_char"], r["char"]) for r in review_rows(literal_path)}, {("醜時", "丑時")})
        self.assertEqual(to_traditional("醜時"), "丑時")
        self.assertEqual(to_traditional("丑時"), "丑時")
        for literal in ("醜惡", "醜陋", "醜時者"):
            self.assertEqual(to_traditional(literal), literal)

    def test_twenty_second_batch_keeps_source_history_and_contextual_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_22}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_22}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 22), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_22]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("二妹", ("ji6 mui2", "ji6 mui6")),
            ("久旱不雨", ("gau2 hon5 bat1 jyu6", "gau2 hon5 bat1 jyu5")),
            ("人溺己溺", ("jan4 nik6 gei2 nik6", "jan4 nik1 gei2 nik1")),
            ("五棓子", ("ng5 bui6 zi2", "ng5 pui5 zi2")),
            ("交角券", ("gaau1 gok3 hyun3", "gaau1 gok3 gyun3")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        self.assertIn(("人為因素", "jan4 wai4 jan1 sou3"), pairs)
        self.assertIn(("人為財死", "jan4 wai6 coi4 sei2"), pairs)
        self.assertTrue({"享帚自珍", "人極計生", "人事不醒", "乳間股腳"}.issubset({r["char"] for r in batch}))
        self.assertTrue({"乾闥婆", "五行字", "人心果李"}.issubset({r["char"] for r in review if r["verdict"] == "defer"}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"亮子", "京油子", "人保公司", "人武惟揚", "人之長情", "人情事故"}))
        literal_path = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(literal_path.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        self.assertEqual({(r["previous_char"], r["char"]) for r in review_rows(literal_path)}, {("人工幹預", "人工干預")})
        for previous, current in (("幹雲蔽日", "干雲蔽日"), ("二週目", "二周目"), ("交流乾擾", "交流干擾"), ("人工幹預", "人工干預")):
            self.assertEqual(to_traditional(previous), current)
            self.assertEqual(to_traditional(current), current)
        for word in ("幹部", "幹線", "週末", "週年", "乾燥", "人工幹預者"):
            self.assertEqual(to_traditional(word), word)

    def test_twenty_third_batch_preserves_history_and_valid_contextual_alternates(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_23}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_23}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 23), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_23]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("仁者樂山", ("jan4 ze2 ngaau6 saan1", "jan4 ze2 ngaau4 saan1")),
            ("什錦餡", ("zaap6 gam2 haam2", "zaap6 gam2 haam6")),
            ("以正視聽", ("ji5 zing3 si6 ting3", "ji5 zing3 si6 ting1", "ji5 zing3 si6 teng1")),
            ("住宅小區", ("zyu6 zaak2 siu2 keoi1", "zyu6 zaak6 siu2 keoi1")),
            ("併案處理", ("bing3 on3 cyu2 lei5", "bing6 on3 cyu2 lei5", "ping3 on3 cyu2 lei5")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("什件", "sap6 gin6"), ("供述動機", "gung1 seot6 dung6 gei1"),
                         ("伺機而動", "zi6 gei1 ji4 dung6"), ("佯降", "joeng4 hong4"),
                         ("低質量", "dai1 zat1 loeng6")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"令狐沖笑", "保法止", "份兒飯", "供水幹管", "伴侶蛋白"}))
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))

    def test_twenty_fourth_batch_has_contextual_codes_without_obscure_draft_promotions(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_24}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_24}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 24), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_24]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("倦怠感", ("gyun6 toi5 gam2", "gyun6 doi6 gam2")),
            ("倩人捉刀", ("sin6 jan4 zuk1 dou1", "sin3 jan4 zuk1 dou1")),
            ("傳奇人物", ("zyun6 kei4 jan4 mat6", "cyun4 kei4 jan4 mat6")),
            ("傾下", ("king1 haa5", "king1 haa6")),
            ("兄弟姐妹", ("hing1 dai6 ze2 mui6", "hing1 dai6 ze2 mui2")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("倒三角", "dou3 saam1 gok3"), ("倒也不是", "dou3 jaa5 bat1 si6"),
                         ("家具行", "gaa1 geoi6 hong4"), ("停刊處分", "ting4 hon1 cyu2 fan6"),
                         ("傾聽意見", "king1 teng1 ji3 gin3"), ("充滿著", "cung1 mun5 zoek6")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"傀奇", "儘儘", "偷下去", "倚馬可待", "優化大師", "兄貴"}))
        self.assertTrue({"偉大祖國", "優秀黨員"}.issubset({r["char"] for r in batch}))
        grade_path = REVIEW.parent / meta["existing_reading_grade_review_path"]
        self.assertEqual(hashlib.sha256(grade_path.read_bytes()).hexdigest(), meta["existing_reading_grade_review_sha256"])
        self.assertEqual([(r["char"], r["jyutping"], r["previous_pron_rank"], r["pron_rank"]) for r in review_rows(grade_path)],
                         [("優惠券", "jau1 wai6 gyun3", "預設", "常用")])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["優惠券", "jau1 wai6 hyun3"], "預設")
        self.assertEqual(ranks["優惠券", "jau1 wai6 gyun3"], "常用")
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))

    def test_twenty_fifth_batch_has_contextual_codes_without_obscure_draft_promotions(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_25}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_25}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 25), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_25]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("公筷母匙", ("gung1 faai3 mou5 si4", "gung1 faai3 mou5 ci4")),
            ("六粒裝", ("luk6 nap1 zong1", "luk6 lap1 zong1")),
            ("共犯論處", ("gung6 faan6 leon6 cyu2", "gung6 faan2 leon6 cyu2")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("兒童玩具", "ji4 tung4 wun6 geoi6"), ("兒女親家", "ji4 neoi5 can3 gaa1"),
                         ("內容摘要", "noi6 jung4 zaak6 jiu3"), ("八斤重", "baat3 gan1 cung5"),
                         ("公使團", "gung1 si3 tyun4"), ("兵多將廣", "bing1 do1 zoeng3 gwong2"),
                         ("典當行", "din2 dong3 hong4")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"光彩陸離", "先聲後實", "八具", "公差費", "兼併額", "兵籍號碼"}))
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))

    def test_twenty_sixth_batch_has_contextual_codes_without_obscure_draft_promotions(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_26}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_26}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 26), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_26]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("准入條件", ("zeon2 jap6 tiu4 gin2", "zeon2 jap6 tiu4 gin6")),
            ("冷眼相覷", ("laang5 ngaan5 soeng1 ceoi3", "laang5 ngaan5 soeng1 zeoi3")),
            ("划行", ("waa4 hang4", "waa1 hang4")),
            ("判處死刑", ("pun3 cyu5 sei2 jing4", "pun3 cyu2 sei2 jing4", "pun3 cyu3 sei2 jing4")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("再試一下", "zoi3 si3 jat1 haa5"), ("冠帽", "gun1 mou2"),
                         ("初始密碼", "co1 ci2 mat6 maa5"), ("叛徒", "bun6 tou4"),
                         ("到齊", "dou3 cai4"), ("制禮作樂", "zai3 lai5 zok3 ngok6")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"冀北空羣", "冰川隙", "分子磁矩", "制粒機", "別介", "別價"}))
        pending = {r["char"] for r in review if r["verdict"] == "defer"}
        self.assertEqual(len(pending), 7)
        self.assertIn("划不來", pending)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))

    def test_twenty_seventh_batch_retains_daily_readings_and_rejects_obscure_additions(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_27}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_27}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 27), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_27]
        self.assertEqual(len(batch), meta["added_rows"])
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, jp in [("剛醒", "gong1 seng2"), ("副領隊", "fu3 ling5 deoi2"),
                         ("動彈不得", "dung6 daan6 bat1 dak1"), ("十九樓", "sap6 gau2 lau4"),
                         ("前緊後鬆", "cin4 gan2 hau6 sung1"), ("克制不住", "hak1 zai3 bat1 zyu6")]:
            self.assertIn((word, jp), pairs)
        for word, readings in [("劣質奶粉", ("lyut3 zat1 naai5 fan2", "lyut6 zat1 naai5 fan2")),
                               ("劣跡昭著", ("lyut3 zik1 ciu1 zoek3", "lyut3 zik1 ziu1 zoek3")),
                               ("動物解剖", ("dung6 mat6 gaai2 fau2", "dung6 mat6 gaai2 pau2")),
                               ("前仆後繼", ("cin4 fu6 hau6 gai3", "cin4 puk1 hau6 gai3"))]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        self.assertTrue({"北京烤鴨", "勞動合同", "副省長", "剪指甲"}.issubset({r["char"] for r in batch}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"勻溜", "加塞", "匡救彌縫", "剸繁決劇", "化學偶聯", "劈哩啪啦"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"劈哩啪啦"})
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["劣質奶粉", "lyut3 zat1 naai5 fan2"], "預設")
        self.assertEqual(ranks["劣質奶粉", "lyut6 zat1 naai5 fan2"], "常用")
        for word, jp in [("副領隊", "fu3 ling5 deoi2"), ("劫持人質", "gip3 ci4 jan4 zi3")]:
            self.assertEqual(ranks[word, jp], "預設")
        for literal in ("前仆后继", "前仆後繼", "前僕後繼"):
            self.assertEqual(to_traditional(literal), "前仆後繼")
            self.assertEqual(to_traditional(to_traditional(literal)), "前仆後繼")
        for literal in ("僕人", "男僕", "公僕", "僕僕風塵"):
            self.assertEqual(to_traditional(literal), literal)
        for literal in ("克制不住", "剋制不住"):
            self.assertEqual(to_traditional(literal), "克制不住")
        self.assertEqual(to_traditional("剋死"), "剋死")
        ledger = REVIEW.parent / meta["existing_literal_review_path"]
        self.assertEqual(hashlib.sha256(ledger.read_bytes()).hexdigest(), meta["existing_literal_review_sha256"])
        self.assertEqual([(r["previous_char"], r["char"], r["action"]) for r in review_rows(ledger)],
                         [("前僕後繼", "前仆後繼", "coalesce")])

    def test_twenty_eighth_batch_keeps_supported_variants_and_filters_obscure_words(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_28}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_28}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 28), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_28]
        self.assertEqual(len(batch), 817)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("參差不一", ("cam1 ci1 bat1 jat1", "caam1 ci1 bat1 jat1")),
            ("及時處理", ("kap6 si4 cyu5 lei5", "kap6 si4 cyu2 lei5")),
            ("友好相處", ("jau5 hou2 soeng1 cyu5", "jau5 hou2 soeng1 cyu2")),
            ("臥室傢俱", ("ngo6 sat1 gaa1 geoi6", "ngo6 sat1 gaa1 keoi1")),
            ("口腔黏膜", ("hau2 hong1 nim1 mok2", "hau2 hong1 nim1 mok6", "hau2 hong1 nim4 mok6")),
            ("十成把握", ("sap6 sing4 baa2 ak1", "sap6 sing4 baa2 ngak1", "sap6 sing4 baang2 ak1")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("卡式錄音機", "kaa1 sik1 luk6 jam1 gei1"), ("卡費", "kaat1 fai3"),
                         ("卷冊", "gyun3 caak3"), ("十發十中", "sap6 faat3 sap6 zung3"),
                         ("口腔潰瘍", "hau2 hong1 kui2 joeng4"), ("古董鋪", "gu2 dung2 pou3")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"十圍五攻", "博察", "友風子雨", "印模石膏", "卡機"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"卡機"})
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 73)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["參差不一", "cam1 ci1 bat1 jat1"], "預設")
        self.assertEqual(ranks["參差不一", "caam1 ci1 bat1 jat1"], "常用")
        self.assertEqual(ranks["及時處理", "kap6 si4 cyu5 lei5"], "預設")
        self.assertEqual(ranks["及時處理", "kap6 si4 cyu2 lei5"], "常用")

    def test_twenty_ninth_batch_preserves_contextual_readings_without_promoting_cold_words(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_29}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_29}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 29), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_29]
        self.assertEqual(len(batch), 659)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("呱呱墮地", ("gu1 gu1 do6 dei6", "waa1 waa1 do6 dei6")),
            ("和平相處", ("wo4 ping4 soeng1 cyu5", "wo4 ping4 soeng1 cyu2")),
            ("咕嚕咕嚕", ("gu1 lou1 gu1 lou1", "gu1 lu1 gu1 lu1")),
            ("名片盒", ("ming4 pin2 hap6", "ming4 pin3 hap6")),
            ("吼起來", ("haau1 hei2 loi4", "hau3 hei2 loi4")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("可說服", "ho2 seoi3 fuk6"), ("吃宵夜", "hek3 siu1 je2"),
                         ("各取所長", "gok3 ceoi2 so2 coeng4"), ("各行其道", "gok3 hang4 kei4 dou6"),
                         ("同行同業", "tung4 hong4 tung4 jip6"), ("名人傳", "ming4 jan4 zyun6"),
                         ("命令行", "ming6 ling6 hong4"), ("咖啡吧", "gaa3 fe1 baa1"),
                         ("咬着唇", "ngaau5 zoek6 seon4"), ("含着淚", "ham4 zoek6 leoi6")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({"台海兩岸", "台獨運動", "各部委", "吞嚥困難"}.issubset({r["char"] for r in batch}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"可可兒的", "吃零嘴", "同惡相黨", "名鞿利鞚", "含牙戴角", "呋喃糖"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"合會", "合調", "同氣", "和裁會", "咪咪叫"})
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 249)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, jp in [("吃宵夜", "hek3 siu1 je2"), ("可緩和", "ho2 wun6 wo4"), ("合理要求", "hap6 lei5 jiu1 kau4")]:
            self.assertEqual(ranks[word, jp], "預設")
        self.assertEqual(ranks["名片盒", "ming4 pin3 hap6"], "常用")

    def test_thirtieth_batch_distinguishes_contextual_tones_and_keeps_familiar_phrases(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_30}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_30}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 30), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_30]
        self.assertEqual(len(batch), 566)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("哄勸", ("hung6 hyun3", "hung3 hyun3")),
            ("嗓子疼", ("song2 zi2 tang4", "song1 zi2 tang4")),
            ("品質惡劣", ("ban2 zat1 ok3 lyut3", "ban2 zat1 ok3 lyut6")),
            ("商會會長", ("soeng1 wui2 wui6 zoeng2", "soeng1 wui6 wui6 zoeng2")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("咽不下", "jin3 bat1 haa6"), ("品相", "ban2 soeng3"),
                         ("商量一下", "soeng1 loeng4 jat1 haa5"), ("喉嚨乾", "hau4 lung4 gon1"),
                         ("喪妻之痛", "song3 cai1 zi1 tung3"), ("喪親之痛", "song3 can1 zi1 tung3"),
                         ("單卡", "daan1 kaat1"), ("嗎啡中毒", "maa1 fe1 zung3 duk6"),
                         ("嗶嗶聲", "bit1 bit1 seng1"), ("因病請假", "jan1 beng6 cing2 gaa3")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({"哪份", "哪句", "喝粥", "喝藥", "四季如畫", "國企改革", "國務總理"}.issubset({r["char"] for r in batch}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"哀梨蒸食", "咽旁間隙", "哥兒義氣", "噴鼻兒香", "四荒八極", "固相聚合"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"咿咿唔唔", "咿唔", "商調", "喔喔叫", "嗲地", "嗶哩啪啦", "哽住"})
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 479)
        self.assertEqual(meta["third_pass_familiarity_restorations"], 51)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["嗓子疼", "song2 zi2 tang4"], "預設")
        self.assertEqual(ranks["嗓子疼", "song1 zi2 tang4"], "常用")
        self.assertEqual(ranks["嚴格要求", "jim4 gaak3 jiu1 kau4"], "預設")

    def test_thirty_first_batch_distinguishes_locations_variants_and_advance_payment(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_31}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_31}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(len(review), meta["review_rows"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 31), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_31]
        self.assertEqual(len(batch), 826)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("國產轎車", ("gwok3 caan2 giu2 ce1", "gwok3 caan2 giu6 ce1")),
            ("坎坷人生", ("ham1 ho1 jan4 sang1", "ham2 ho2 jan4 sang1")),
            ("報名條件", ("bou3 ming4 tiu4 gin2", "bou3 ming4 tiu4 gin6")),
            ("圖片鏈接", ("tou4 pin2 lin2 zip3", "tou4 pin2 lin4 zip3")),
            ("塑膠袋", ("sou3 gaau1 doi2", "sok3 gaau1 doi2", "sou3 gaau1 doi6")),
            ("墊錢", ("din6 cin2", "zin3 cin2")),
            ("垃圾郵件", ("laap6 saap3 jau4 gin2", "laap6 saap3 jau4 gin6")),
            ("地下水位", ("dei6 haa6 seoi2 wai2", "dei6 haa6 seoi2 wai6")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for word, jp in [("國恥日", "gwok3 ci2 jat6"), ("國難財", "gwok3 naan6 coi4"),
                         ("圖書館長", "tou4 syu1 gun2 zoeng2"), ("在思想上", "zoi6 si1 soeng2 soeng6"),
                         ("在朝黨", "zoi6 ciu4 dong2"), ("地磅", "dei6 bong2"),
                         ("地縫裏", "dei6 fung6 leoi5"), ("坐而待斃", "zo6 ji4 doi6 bai6"),
                         ("墊上運動", "zin3 soeng6 wan6 dung6"), ("塵肺病", "can4 fai3 beng6")]:
            self.assertIn((word, jp), pairs)
        self.assertTrue({"國小", "國新辦", "團委書記", "基本資料", "填寫表格", "墜入情網"}.issubset({r["char"] for r in batch}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"圓木警枕", "土豆皮", "地盡其力", "坐卧針氈", "域控制器", "基因座", "堅額健舌"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"塑膠泡綿"})
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 114)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["報名條件", "bou3 ming4 tiu4 gin2"], "預設")
        self.assertEqual(ranks["墊錢", "din6 cin2"], "預設")
        self.assertEqual(ranks["墊錢", "zin3 cin2"], "常用")

    def test_thirty_second_batch_preserves_modern_readings_and_filters_obscure_phrases(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_32}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_32}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 32), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_32]
        self.assertEqual(len(batch), 785)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("增產率", ("zang1 caan2 leot2", "zang1 caan2 leot6")),
            ("外科病房", ("ngoi6 fo1 beng6 fong2", "ngoi6 fo1 beng6 fong4")),
            ("夜半三更", ("je6 bun3 saam1 gaang1", "je6 bun3 saam1 gang1")),
            ("大使夫人", ("daai6 si5 fu1 jan4", "daai6 si3 fu1 jan4")),
            ("大姑丈", ("daai6 gu1 zoeng2", "daai6 gu1 zoeng6")),
            ("大笑話", ("daai6 siu3 waa2", "daai6 siu3 waa6")),
            ("夾心糖", ("gaap3 sam1 tong2", "gaap3 sam1 tong4")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for pair in [("夏收夏種", "haa6 sau1 haa6 zung3"), ("夠重", "gau3 cung5"),
                     ("大匙", "daai6 ci4"), ("大漲大跌", "daai6 zoeng2 daai6 dit3"),
                     ("大崩盤", "daai6 bang1 pun4"), ("太過分", "taai3 gwo3 fan6"),
                     ("天蠍女", "tin1 kit3 neoi5"), ("失着", "sat1 zoek6")]:
            self.assertIn(pair, pairs)
        for pair in [("大使夫人", "daai6 sai2 fu1 jan4"), ("太過分", "taai3 gwo3 fan1"),
                     ("夜半三更", "je6 bun3 saam1 gang3"), ("天蠍女", "tin1 hit3 neoi5")]:
            self.assertNotIn(pair, pairs)
        self.assertTrue({"大盤雞", "大滷麵", "大箱子", "大柱子", "多喝水", "夜涼如水"}.issubset({r["char"] for r in batch}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"大才榱槃", "天之僇民", "奇硬無比", "大中小學校", "夾槍帶棍"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"大房"})
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 23)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["大使夫人", "daai6 si5 fu1 jan4"], "預設")
        self.assertEqual(ranks["大使夫人", "daai6 si3 fu1 jan4"], "常用")
        self.assertEqual(ranks["夜半三更", "je6 bun3 saam1 gaang1"], "預設")
        self.assertEqual(ranks["夜半三更", "je6 bun3 saam1 gang1"], "常用")

    def test_thirty_third_batch_distinguishes_fondness_offices_and_attested_variants(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_33}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_33}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 33), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_33]
        self.assertEqual(len(batch), 935)
        self.assertTrue(all(r["ingested_char"] for r in review if r["verdict"] == "accept"))
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for word, readings in [
            ("女大使", ("neoi5 daai6 si5", "neoi5 daai6 si3")),
            ("女院長", ("neoi5 jyun2 zoeng2", "neoi5 jyun6 zoeng2")),
            ("女生宿舍", ("neoi5 saang1 suk1 se3", "neoi5 sang1 suk1 se3")),
            ("婉轉動聽", ("jyun2 zyun2 dung6 ting3", "jyun2 zyun2 dung6 teng1", "jyun2 zyun2 dung6 ting1")),
            ("孽債", ("jip6 zaai3", "jit6 zaai3")),
            ("客戶檔案", ("haak3 wu6 dong2 on3", "haak3 wu6 dong3 on3")),
            ("蜿蜒行進", ("jyun1 jin4 hang4 zeon3", "jyun2 jin4 hang4 zeon3")),
        ]:
            self.assertTrue({(word, jp) for jp in readings}.issubset(pairs), word)
        for pair in [("奪人所好", "dyut6 jan4 so2 hou3"), ("女校長", "neoi5 haau6 zoeng2"),
                     ("好出風頭", "hou3 ceot1 fung1 tau4"), ("好學易用", "hou2 hok6 ji6 jung6"),
                     ("奶奶家", "naai4 naai2 gaa1"), ("嫵媚動人", "mou5 mei6 dung6 jan4"),
                     ("娩出", "min5 ceot1"), ("孤嶼", "gu1 zeoi6"),
                     ("學生會長", "hok6 saang1 wui2 zoeng2"), ("學識上", "hok6 sik1 soeng6"),
                     ("孕媽咪", "jan6 maa1 mi4")]:
            self.assertIn(pair, pairs)
        for pair in [("女大使", "neoi5 daai6 sai2"), ("女校長", "neoi5 haau6 coeng4"),
                     ("好學易用", "hou3 hok6 ji6 jung6"), ("娩出", "faan3 ceot1"),
                     ("孤嶼", "gu1 jyu4"), ("學識上", "hok6 sik1 soeng5")]:
            self.assertNotIn(pair, pairs)
        self.assertTrue({"好久不見", "好聚好散", "孤枕難眠", "女同事", "客家方言", "學生家長"}.issubset({r["char"] for r in batch}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"奉辭伐罪", "如塤如箎", "孚尹明達", "孤犢觸乳", "委肉虎蹊"}))
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"孃兒倆"})
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 50)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["女院長", "neoi5 jyun2 zoeng2"], "預設")
        self.assertEqual(ranks["女院長", "neoi5 jyun6 zoeng2"], "常用")
        self.assertEqual(ranks["婉轉動聽", "jyun2 zyun2 dung6 ting3"], "預設")
        self.assertEqual(ranks["嫵媚動人", "mou5 mei6 dung6 jan4"], "預設")
        self.assertEqual(ranks["孕媽咪", "jan6 maa1 mi4"], "預設")

    def test_thirty_fourth_batch_preserves_whole_word_readings_and_common_expressions(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_34}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_34}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 34), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_34]
        self.assertEqual(len(batch), 1110)
        self.assertTrue(all(r["ingested_char"] for r in review if r["verdict"] == "accept"))
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("家無長物", "gaa1 mou4 zoeng6 mat6"), ("將軍令", "zoeng1 gwan1 ling6"),
                     ("將進酒", "coeng1 zeon3 zau2"), ("對着", "deoi3 zoek6"),
                     ("小便宜", "siu2 pin4 ji2"), ("小便宜", "siu2 pin4 ji4"),
                     ("寒蟬悽切", "hon4 sim4 cai1 cit3"), ("寒蟬悽切", "hon4 sin4 cai1 cit3"),
                     ("射籃得分", "se6 laam2 dak1 fan1"), ("射籃得分", "se6 laam4 dak1 fan1"),
                     ("尋到", "cam4 dou2"), ("尋到", "cam4 dou3"),
                     ("小學校長", "siu2 hok6 haau6 zoeng2"), ("少校軍官", "siu3 haau6 gwan1 gun1"),
                     ("小廚房", "siu2 cyu4 fong2"), ("小商小販", "siu2 soeng1 siu2 faan2")]:
            self.assertIn(pair, pairs)
        for pair in [("家無長物", "gaa1 mou4 coeng4 mat6"), ("將軍令", "zoeng3 gwan1 ling6"),
                     ("將進酒", "zoeng1 zeon3 zau2"), ("小學校長", "siu2 hok6 haau6 coeng4"),
                     ("少校軍官", "siu3 gaau3 gwan1 gun1"), ("小廚房", "siu2 ceoi4 fong2")]:
            self.assertNotIn(pair, pairs)
        words = {r["char"] for r in batch}
        self.assertTrue({"家庭醫生", "寄掛號信", "寫封信", "小土豆", "寡女", "小角色", "寵物用品"}.issubset(words))
        self.assertTrue(words.isdisjoint({"寄生電容", "寡核苷酸", "封胡羯末", "寸轄制輪", "少若成性", "實是"}))
        self.assertFalse(any(r["verdict"] == "defer" for r in review))
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 144)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for pair in [("家無長物", "gaa1 mou4 zoeng6 mat6"), ("將進酒", "coeng1 zeon3 zau2"),
                     ("射籃得分", "se6 laam2 dak1 fan1"), ("小便宜", "siu2 pin4 ji2"),
                     ("小商小販", "siu2 soeng1 siu2 faan2")]:
            self.assertEqual(ranks[pair], "預設", pair)
        self.assertEqual(ranks["寒蟬悽切", "hon4 sin4 cai1 cit3"], "常用")

    def test_thirty_fifth_batch_keeps_whole_word_readings_and_consistent_withdrawals(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_35}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_35}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 0)
        self.assertEqual(input_fingerprint(curated, meta, 35), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_35]
        self.assertEqual(len(batch), 1076)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertTrue(all(r["ingested_char"] == to_traditional(r["char"]) for r in review if r["verdict"] == "accept"))
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("平生之願", "ping4 sang1 zi1 jyun6"), ("屬意於", "zuk1 ji3 jyu1"),
                     ("屢仆屢起", "leoi5 fu6 leoi5 hei2"), ("屢仆屢起", "leoi5 puk1 leoi5 hei2"),
                     ("屋檐下", "uk1 jim4 haa6"), ("屋檐下", "uk1 jam4 haa6"), ("屋檐下", "uk1 sim4 haa6"),
                     ("屏息靜觀", "bing2 sik1 zing6 gun1"), ("左胳膊", "zo2 gaak3 bok3"),
                     ("幾件事", "gei2 gin6 si6"), ("瞭望塔", "liu4 mong6 taap3"),
                     ("年月日時", "nin4 jyut6 jat6 si4"), ("干擾器", "gon1 jiu2 hei3")]:
            self.assertIn(pair, pairs)
        for pair in [("平生之願", "ping4 saang1 zi1 jyun6"), ("屬意於", "suk6 ji3 jyu1"),
                     ("屢仆屢起", "leoi5 buk6 leoi5 hei2"), ("屏息靜觀", "ping4 sik1 zing6 gun1"),
                     ("瞭望塔", "liu6 mong6 taap3"), ("巧取豪奪", "haau2 tau1 hou4 dyut6")]:
            self.assertNotIn(pair, pairs)
        withdrawn = {to_traditional(r["char"]) for r in review if r["verdict"] == "reject" and r["note"].startswith("常用度第二輪複核")}
        self.assertTrue({to_traditional(r["char"]) for r in batch}.isdisjoint(withdrawn))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"干撓", "干擾測試", "尾生之信", "屢見疊出"}))
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 207)
        self.assertTrue({"巧取豪奪", "平行四邊形"}.issubset(
            {r["char"] for r in review if r["verdict"] == "already_present"}))
        self.assertFalse(any(r["verdict"] == "defer" for r in review))
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["屢仆屢起", "leoi5 fu6 leoi5 hei2"], "預設")
        self.assertEqual(ranks["屢仆屢起", "leoi5 puk1 leoi5 hei2"], "常用")
        self.assertEqual(ranks["左胳膊", "zo2 gaak3 bok3"], "預設")

    def test_falling_and_interference_literals_survive_normalization(self):
        for expected, inputs in [
            ("屢仆屢起", ("屡仆屡起", "屢仆屢起", "屢僕屢起")),
            ("干擾力", ("干扰力", "干擾力", "幹擾力")),
            ("干擾哨聲", ("干扰哨声", "干擾哨聲", "幹擾哨聲")),
            ("干擾器", ("干扰器", "干擾器", "幹擾器")),
            ("干礙", ("干碍", "干礙", "幹礙")),
            ("干連", ("干连", "干連", "幹連")),
        ]:
            for literal in inputs:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        for literal in ("僕人", "男僕", "公僕", "幹部", "乾燥", "乾坤", "幹擾源頭", "抗幹擾性能"):
            self.assertEqual(to_traditional(literal), literal)

    def test_thirty_sixth_batch_keeps_spoken_variants_and_rejects_obscure_extensions(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_36}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_36}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(input_fingerprint(curated, meta, 36), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_36]
        self.assertEqual(len(batch), 850)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertTrue(all(r["ingested_char"] == to_traditional(r["char"]) for r in review if r["verdict"] == "accept"))
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("幾無二致", "gei1 mou4 ji6 zi3"), ("幾近於", "gei1 gan6 jyu1"),
                     ("幾行字", "gei2 hong4 zi6"), ("度假勝地", "dou6 gaa3 sing3 dei6"),
                     ("廚房用品", "cyu4 fong2 jung6 ban2"), ("廚房用品", "cyu4 fong4 jung6 ban2"),
                     ("廚房用品", "ceoi4 fong2 jung6 ban2"), ("彈出", "daan6 ceot1"), ("彈出", "taan4 ceot1"),
                     ("強加於", "koeng5 gaa1 jyu1"), ("強制保險", "koeng5 zai3 bou2 him2"),
                     ("強制保險", "koeng4 zai3 bou2 him2"), ("很重", "han2 cung5"),
                     ("彷佛", "fong2 fat1"), ("彷如", "fong2 jyu4"), ("往上爬", "wong5 soeng6 paa4"),
                     ("彩雲追月", "coi2 wan4 zeoi1 jyut6"), ("御駕親征", "jyu6 gaa3 can1 zing1"),
                     ("復辟事件", "fuk6 bik1 si6 gin2"), ("復辟事件", "fuk6 pik1 si6 gin2"),
                     ("獼猴桃", "nei4 hau4 tou2"), ("獼猴桃", "nei4 hau4 tou4"), ("很久沒", "han2 gau2 mut6")]:
            self.assertIn(pair, pairs, pair)
        for pair in [("幾行字", "gei2 haang4 zi6"), ("度假勝地", "dou6 gaa2 sing3 dei6"),
                     ("彈出", "daan2 ceot1"), ("彷佛", "pong4 fat6"), ("很重", "han2 cung4"),
                     ("彩雲追月", "coi2 wan4 zeoi1 jyut2"), ("沿用", "jin4 jung6")]:
            self.assertNotIn(pair, pairs)
        withdrawn = {to_traditional(r["char"]) for r in review if r["verdict"] == "reject" and r["note"].startswith("常用度第二輪複核")}
        self.assertTrue({to_traditional(r["char"]) for r in batch}.isdisjoint(withdrawn))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"引線鍵合", "復子明辟", "律度", "微壓計"}))
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 660)
        self.assertEqual(meta["existing_runtime_readings_mirrored"], 1)
        self.assertEqual({r["char"] for r in review if r["verdict"] == "defer"}, {"待會"})
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("彈出", "daan6 ceot1", "taan4 ceot1"),
                                         ("廚房用品", "cyu4 fong2 jung6 ban2", "ceoi4 fong2 jung6 ban2"),
                                         ("獼猴桃", "nei4 hau4 tou2", "nei4 hau4 tou4")]:
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")

    def test_thirty_seventh_batch_separates_word_familiarity_and_context_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_37}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_37}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(input_fingerprint(curated, meta, 37), meta["input_curated_sha256"])
        batch = [r for r in curated if r.get("batch") == BATCH_37]
        self.assertEqual(len(batch), 762)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertTrue(all(r["ingested_char"] == to_traditional(r["char"]) for r in review if r["verdict"] == "accept"))
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("心手相應", "sam1 sau2 soeng1 jing3"), ("心情愉快", "sam1 cing4 jyu4 faai3"),
                     ("忍受着", "jan2 sau6 zoek6"), ("性交易", "sing3 gaau1 jik6"),
                     ("悲咽", "bei1 jit3"), ("悽咽", "cai1 jit3"), ("情見於色", "cing4 jin6 jyu1 sik1"),
                     ("怕老婆", "paa3 lou5 po4")]:
            self.assertIn(pair, pairs, pair)
        for pair in [("心如止水", "sam1 tung4 zi2 seoi2"), ("心情愉快", "sam1 cing4 jyu6 faai3"),
                     ("性交易", "sing3 gaau1 ji6"), ("畢竟", "bit1 ging2"),
                     ("惡習不改", "ok3 sing3 bat1 goi2"), ("悲咽", "bei1 jin3"),
                     ("情見於色", "cing4 gin3 jyu1 sik1"), ("怕吃苦", "paa3 hek6 fu2")]:
            self.assertNotIn(pair, pairs)
        withdrawn = {to_traditional(r["char"]) for r in review if r["verdict"] == "reject" and r["note"].startswith("常用度第二輪複核")}
        self.assertTrue({to_traditional(r["char"]) for r in batch}.isdisjoint(withdrawn))
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        for word in ("快玩", "快適", "心要", "想裝", "想靠"):
            self.assertIn("語境", rejected[word]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", rejected[word]["reading_reference"])
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"微帶菜色", "忠貫白日", "性骨折", "想裝"}))
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 633)
        self.assertEqual(meta["third_pass_familiarity_restorations"], 8)
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("忍到", "jan2 dou3", "jan2 dou2"),
                                         ("忸怩不安", "nau2 nei4 bat1 on1", "nuk6 nei4 bat1 on1"),
                                         ("惡跡昭著", "ok3 zik1 ciu1 zyu3", "ok3 zik1 ziu1 zyu3"),
                                         ("性虐待狂", "sing3 joek6 doi6 kwong4", "sing3 joek6 doi6 kong4")]:
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")

    def test_thirty_eighth_batch_keeps_common_phrases_and_contextual_reading_order(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_38}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_38}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 38), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        batch = [r for r in curated if r.get("batch") == BATCH_38]
        self.assertEqual(len(batch), 854)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        self.assertTrue(all(r["ingested_char"] == to_traditional(r["char"]) for r in review if r["verdict"] == "accept"))
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("感到痛苦", "gam2 dou3 tung3 fu2"), ("手指畫", "sau2 zi2 waa2"),
                     ("手指縫", "sau2 zi2 fung6"), ("手倒立", "sau2 dou2 laap6"),
                     ("打水仗", "daa2 seoi2 zoeng3"), ("所累", "so2 leoi6")]:
            self.assertIn(pair, pairs)
        for pair in [("感到痛苦", "gam2 dou2 tung3 fu2"), ("手指畫", "sau2 zi2 waak6"),
                     ("手倒立", "sau2 dou3 laap6"), ("所累", "so2 leoi5")]:
            self.assertNotIn(pair, pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("意料不到", "ji3 liu6 bat1 dou2", "ji3 liu6 bat1 dou3"),
                                         ("慢慢而行", "maan6 maan2 ji4 haang4", "maan6 maan1 ji4 haang4"),
                                         ("房車賽", "fong2 ce1 coi3", "fong4 ce1 coi3"),
                                         ("愛我嗎", "oi3 ngo5 maa3", "oi3 ngo5 maa1"),
                                         ("打聽一下", "daa2 ting1 jat1 haa5", "daa2 ting3 jat1 haa5"),
                                         ("扔出來", "wing1 ceot1 loi4", "jing4 ceot1 loi4"),
                                         ("扛着", "kong1 zoek6", "gong1 zoek6")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        self.assertTrue({"成大", "戰雷頭", "截錐", "意廣才疏", "慣量橢球"}.issubset(rejected))
        self.assertIn("跨詞", rejected["成大"]["note"])
        self.assertIn("Cantopop-corpus/blob/018e885", rejected["成大"]["reading_reference"])
        handsaw = next(r for r in review if r["char"] == "手鋸" and r["verdict"] == "accept")
        self.assertIn("跨詞", handsaw["note"])
        self.assertIn("jyut.net/query?q=鋸", handsaw["reading_reference"])
        self.assertTrue(all(r["proposed_usage_rank"] in {"0", "1", "2"} and r["proposed_usage_note"]
                            for r in review if r["verdict"] == "accept"))
        for expected, inputs in [("手制動", ("手制动", "手制動", "手製動")),
                                 ("手制動器", ("手制动器", "手制動器", "手製動器"))]:
            self.assertIn((expected, "sau2 zai3 dung6" + (" hei3" if expected.endswith("器") else "")), pairs)
            for literal in inputs:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        for literal in ("手製", "製造", "製動者", "手製動畫"):
            self.assertEqual(to_traditional(literal), literal)

    def test_thirty_ninth_batch_checks_complete_phrases_and_word_senses(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_39}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_39}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 39), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 125)
        batch = [r for r in curated if r.get("batch") == BATCH_39]
        self.assertEqual(len(batch), 1254)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("批假", "pai1 gaa3"), ("抓得緊", "zaau2 dak1 gan2"),
                     ("拋得開", "paau1 dak1 hoi1"), ("折衷方案", "zit3 zung1 fong1 on3"),
                     ("摺下來", "zip3 haa6 loi4"), ("拘泥形式", "keoi1 nei6 jing4 sik1"),
                     ("持正不阿", "ci4 zing3 bat1 o1"), ("持續上升", "ci4 zuk6 soeng5 sing1")]:
            self.assertIn(pair, pairs)
        for pair in [("批假", "pai1 gaa2"), ("折衷方案", "zit3 cung1 fong1 on3"),
                     ("拂去", "bat6 heoi3"), ("拘泥形式", "keoi1 nai4 jing4 sik1"),
                     ("持正不阿", "ci4 zing3 bat1 aa3"), ("拋下", "paau1 haa3")]:
            self.assertNotIn(pair, pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("扳住", "baan2 zyu6", "paan1 zyu6"),
                                         ("抒情散文", "syu1 cing4 saan2 man4", "syu1 cing4 saan2 man2"),
                                         ("抗腫瘤", "kong3 zung2 lau2", "kong3 zung2 lau4"),
                                         ("拴緊", "saan1 gan2", "cyun4 gan2"),
                                         ("拾級而下", "sip3 kap1 ji4 haa6", "sap6 kap1 ji4 haa6")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        for word in ("拖得", "拖拖"):
            self.assertIn("歌詞", rejected[word]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", rejected[word]["reading_reference"])
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"找不着北", "找彆扭"}))
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"拷機", "拷盤", "拳拳在念", "指令預取"}))
        self.assertTrue(all(r["ingested_char"] == to_traditional(r["char"]) and r["proposed_usage_rank"] in {"0", "1", "2"}
                            and r["proposed_usage_note"] for r in review if r["verdict"] == "accept"))

    def test_fortieth_batch_checks_word_senses_and_complete_lyric_context(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_40}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_40}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 40), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 205)
        batch = [r for r in curated if r.get("batch") == BATCH_40]
        self.assertEqual(len(batch), 1174)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("按件計費", "on3 gin2 gai3 fai3"), ("掀被", "hin1 pei5"),
                     ("捻線", "nin2 sin3"), ("排成行", "paai4 sing4 hong4"),
                     ("排長隊", "paai4 coeng4 deoi2"), ("探聽出", "taam3 ting3 ceot1"),
                     ("提在手上", "tai4 zoi6 sau2 soeng6"), ("插槽數", "caap3 cou4 sou3"),
                     ("揹人", "bui3 jan4"), ("推斷出", "teoi1 dyun6 ceot1"), ("掛斗", "gwaa3 dau2")]:
            self.assertIn(pair, pairs)
        for pair in [("挪走", "no5 zau2"), ("掀被", "hin1 bei6"),
                     ("排成行", "paai4 sing4 haang4"), ("提在手上", "tai4 zoi6 sau2 soeng5"),
                     ("插槽數", "caap3 cou4 sou2"), ("揹人", "bui1 jan4"), ("掛斗", "gwaa3 dau3")]:
            self.assertNotIn(pair, pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("挑撥是非", "tiu1 but6 si6 fei1", "tiu5 but6 si6 fei1"),
                                         ("捻線", "nin2 sin3", "nim2 sin3"),
                                         ("探聽出", "taam3 ting3 ceot1", "taam3 ting1 ceot1"),
                                         ("推斷出", "teoi1 dyun6 ceot1", "teoi1 dyun3 ceot1"),
                                         ("揣着", "caai1 zoek6", "cyun2 zoek6")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        self.assertIn("換節目", rejected["換節"]["note"])
        self.assertIn("Cantopop-corpus/blob/018e885", rejected["換節"]["reading_reference"])
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"提溜", "掐架", "捏咕", "捕獲蛋白", "掩模對準"}))
        self.assertTrue(all(r["ingested_char"] == to_traditional(r["char"]) and r["proposed_usage_rank"] in {"0", "1", "2"}
                            and r["proposed_usage_note"] for r in review if r["verdict"] == "accept"))

        for expected, inputs in [("排除干擾", ("排除干扰", "排除干擾", "排除幹擾")),
                                 ("掛斗", ("挂斗", "掛斗", "掛鬥"))]:
            for literal in inputs:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        for literal in ("幹部", "鬥爭", "抗干擾", "干預"):
            self.assertEqual(to_traditional(literal), literal)
        usage = {r["char"]: r for r in review_rows(CURATED.with_name("word_usage.tsv"))}
        self.assertEqual(usage["掛斗"]["essay_frequency"], "342")
        self.assertNotIn("掛鬥", usage)
        self.assertNotIn("排除幹擾", usage)
        judgments = {r["char"] for r in review_rows(CURATED.with_name("word_usage_judgments.tsv"))}
        self.assertNotIn("掛斗", judgments)

    def test_forty_first_batch_preserves_word_senses_and_familiarity_evidence(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_41}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_41}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 41), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 236)
        batch = [r for r in curated if r.get("batch") == BATCH_41]
        self.assertEqual(len(batch), 1183)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("搶救人質", "coeng2 gau3 jan4 zat1"), ("摺疊椅", "zip3 dip6 ji2"),
                     ("撐下去", "caang1 haa6 heoi3"), ("撰寫論文", "zaan6 se2 leon6 man4"),
                     ("操場上", "cou1 coeng4 soeng6"), ("擬具", "ji5 geoi6"),
                     ("播種法", "bo3 zung2 faat3"), ("據云", "geoi3 wan4"),
                     ("改旗易幟", "goi2 kei4 ji6 ci3"), ("擁抱着", "jung2 pou5 zoek6")]:
            self.assertIn(pair, pairs)
        for pair in [("搶救人質", "coeng2 gau3 jan4 zi3"), ("摺疊椅", "zip3 daap6 ji2"),
                     ("撰寫論文", "zaan3 se2 leon6 man4"), ("操場上", "cou1 coeng4 soeng5"),
                     ("擬具", "ji4 geoi6"), ("播種法", "bo3 zung3 faat3"),
                     ("塗脂抹粉", "tou4 zi1 maat3 fan2")]:
            self.assertNotIn(pair, pairs)
        covered = next(r for r in review if r["id"] == "77107")
        self.assertEqual(covered["verdict"], "already_present")
        self.assertIn("tou4 zi1 mut3 fan2", covered["note"])
        self.assertIn("https://jyut.net/query?q=抹", covered["reading_reference"])
        self.assertIn(("熙來攘往", "hei1 loi4 joeng4 wong5"), pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("搖了一下", "jiu4 liu5 jat1 haa5", "jiu4 liu5 jat1 haa6"),
                                         ("搬石砸腳", "bun1 sek6 zaap3 goek3", "bun1 sek6 zaap6 goek3"),
                                         ("摟住", "lau2 zyu6", "lau5 zyu6"),
                                         ("撈獲", "laau4 wok6", "laau1 wok6"),
                                         ("撬開", "giu6 hoi1", "hiu3 hoi1"),
                                         ("擅自處理", "sin6 zi6 cyu2 lei5", "sin6 zi6 cyu5 lei5")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        self.assertIn("相擁／到", rejected["擁到"]["note"])
        self.assertIn("Cantopop-corpus/blob/018e885", rejected["擁到"]["reading_reference"])
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"撒鴨子", "擼子", "操蛋", "擬凸函數", "擴增引物", "攤配"}))
        for literal in ("据云", "據云", "據雲"):
            self.assertEqual(to_traditional(literal), "據云")
            self.assertEqual(to_traditional(to_traditional(literal)), "據云")
        self.assertEqual(to_traditional("雲朵"), "雲朵")
        usage = {r["char"]: r for r in review_rows(CURATED.with_name("word_usage.tsv"))}
        self.assertEqual(usage["據云"]["essay_frequency"], "383")
        self.assertNotIn("據雲", usage)
        judgments = {r["char"] for r in review_rows(CURATED.with_name("word_usage_judgments.tsv"))}
        self.assertNotIn("據云", judgments)

    def test_forty_second_batch_keeps_contextual_sounds_and_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_42}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_42}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 42), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 541)
        batch = [r for r in curated if r.get("batch") == BATCH_42]
        self.assertEqual(len(batch), 752)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("散了架", "saan2 liu5 gaa3"), ("敬上", "ging3 soeng6"),
                     ("文人墨客", "man4 jan4 mak6 haak3"), ("新古典主義", "san1 gu2 din2 zyu2 ji6"),
                     ("斷然拒絕", "dyun3 jin4 keoi5 zyut6"), ("斷然拒絕", "dyun6 jin4 keoi5 zyut6"),
                     ("數數看", "sou2 sou2 hon3"), ("救人如救火", "gau3 jan4 jyu4 gau3 fo2")]:
            self.assertTrue(any(r["char"] == pair[0] and
                                r["verdict"] in {"accept", "already_present"} and
                                (r["jyutping"] == pair[1] or pair[1] in r["note"])
                                for r in review), pair)
        for pair in [("散了架", "saan3 liu5 gaa2"), ("敬上", "ging3 soeng5"),
                     ("文人墨客", "man4 jan4 mak6 si6"), ("數數看", "sou2 sou3 hon3")]:
            self.assertNotIn(pair, pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("故障診斷", "gu3 zoeng3 can2 dyun6", "gu3 zoeng3 can2 dyun3"),
                                         ("整棵樹", "zing2 po1 syu6", "zing2 fo2 syu6"),
                                         ("整衣斂容", "zing2 ji1 lim5 jung4", "zing2 ji1 lim6 jung4"),
                                         ("新郵件", "san1 jau4 gin2", "san1 jau4 gin6")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        for word, boundary in [("放煙", "放／煙花"), ("教上", "教／上帝"), ("斂色", "收斂／色彩")]:
            self.assertIn(boundary, rejected[word]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", rejected[word]["reading_reference"])
        self.assertTrue({r["char"] for r in batch}.isdisjoint({"數九天氣", "敢情是", "整天價", "斷齏畫粥"}))
        usage = {r["char"]: r for r in review_rows(CURATED.with_name("word_usage.tsv"))}
        self.assertEqual(usage[to_traditional("斷然拒絕")]["usage_rank"], "1")
        self.assertEqual(usage[to_traditional("敷好")]["basis"], "essay")
        self.assertEqual(usage[to_traditional("敷好")]["essay_frequency"], "371")

    def test_forty_third_batch_preserves_whole_word_readings_and_divination(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_43}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_43}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 43), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 297)
        batch = [r for r in curated if r.get("batch") == BATCH_43]
        self.assertEqual(len(batch), 710)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("替人着想", "tai3 jan4 zoek6 soeng2"), ("晃來晃去", "fong2 loi4 fong2 heoi3"),
                     ("書面報告", "syu1 min6 bou3 gou3"), ("會員中心", "wui6 jyun4 zung1 sam1"),
                     ("星占學", "sing1 zim1 hok6"), ("早占勿藥", "zou2 zim1 mat6 joek6")]:
            self.assertIn(pair, pairs)
        for pair in [("替人着想", "tai3 jan4 zoek3 soeng2"), ("晃來晃去", "fong6 loi4 fong6 heoi3"),
                     ("書面報告", "syu1 min2 bou3 gou3"), ("會員中心", "wui2 jyun4 zung1 sam1")]:
            self.assertNotIn(pair, pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("旁聽席", "pong4 ting3 zik6", "pong4 ting1 zik6"),
                                         ("旋繞着", "syun4 jiu2 zoek6", "syun4 jiu5 zoek6"),
                                         ("書刊雜誌", "syu1 hon2 zaap6 zi3", "syu1 hon1 zaap6 zi3"),
                                         ("會計公司", "wui6 gai3 gung1 si1", "kui2 gai3 gung1 si1")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        covered = next(r for r in review if r["id"] == "81638")
        self.assertEqual(covered["verdict"], "already_present")
        self.assertIn("sau2 bat1 sik1 gyun2", covered["note"])
        self.assertEqual(ranks["手不釋卷", "sau2 bat1 sik1 gyun3"], "常用")
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        for word, boundary in [("明為", "明明／為時"), ("更當", "傻更更／當然"), ("會服", "會／服從")]:
            self.assertIn(boundary, rejected[word]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", rejected[word]["reading_reference"])
        for bad, good in [("早佔勿藥", "早占勿藥"), ("星佔學", "星占學"), ("星佔術", "星占術")]:
            for literal in (bad, good):
                self.assertEqual(to_traditional(literal), good)
                self.assertEqual(to_traditional(to_traditional(literal)), good)
        self.assertEqual(to_traditional("佔有"), "佔有")

    def test_campaign_and_restoration_literals_keep_their_senses(self):
        for expected, inputs in [("御駕親征", ("御驾亲征", "御駕親征", "御駕親徵")),
                                 ("復辟事件", ("复辟事件", "復辟事件", "復闢事件"))]:
            for literal in inputs:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        for literal in ("徵求", "御駕親徵者", "復闢事件簿", "開闢", "闢謠"):
            self.assertEqual(to_traditional(literal), literal)

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
