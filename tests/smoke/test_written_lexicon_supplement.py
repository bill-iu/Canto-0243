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
BATCH_44 = "2026-11-06-written-b44"
BATCH_45 = "2026-11-06-written-b45"
BATCH_46 = "2026-11-06-written-b46"
BATCH_47 = "2026-11-06-written-b47"
BATCH_48 = "2026-11-06-written-b48"
BATCH_49 = "2026-11-06-written-b49"
BATCH_50 = "2026-11-06-written-b50"
BATCH_51 = "2026-11-06-written-b51"
BATCH_52 = "2026-11-06-written-b52"
BATCH_53 = "2026-11-06-written-b53"
BATCH_54 = "2026-11-06-written-b54"
BATCH_55 = "2026-11-06-written-b55"
BATCH_56 = "2026-11-06-written-b56"
BATCH_57 = "2026-11-06-written-b57"
BATCH_58 = "2026-11-06-written-b58"
BATCH_59 = "2026-11-06-written-b59"
BATCH_60 = "2026-11-06-written-b60"
BATCH_61 = "2026-11-06-written-b61"
BATCH_62 = "2026-11-06-written-b62"
BATCH_63 = "2026-11-06-written-b63"
BATCH_64 = "2026-11-06-written-b64"
BATCH_65 = "2026-11-06-written-b65"
BATCH_66 = "2026-11-06-written-b66"
BATCH_67 = "2026-11-06-written-b67"


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
            "行政處分": ("hang4 zing3 cyu2 fan1", "0493"),
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
        batch = [row for row in json.loads(CURATED.read_text(encoding="utf-8")) if row.get("batch") in {BATCH, BATCH_02, BATCH_03, BATCH_04, BATCH_05, BATCH_06, BATCH_07, BATCH_08, BATCH_09, BATCH_10, BATCH_11, BATCH_12, BATCH_13, BATCH_14, BATCH_15, BATCH_16, BATCH_17, BATCH_18, BATCH_19, BATCH_20, BATCH_21, BATCH_22, BATCH_23, BATCH_24, BATCH_25, BATCH_26, BATCH_27, BATCH_28, BATCH_29, BATCH_30, BATCH_31, BATCH_32, BATCH_33, BATCH_34, BATCH_35, BATCH_36, BATCH_37, BATCH_38, BATCH_39, BATCH_40, BATCH_41, BATCH_42, BATCH_43, BATCH_44, BATCH_45, BATCH_46, BATCH_47, BATCH_48, BATCH_49, BATCH_50, BATCH_51, BATCH_52, BATCH_53, BATCH_54, BATCH_55, BATCH_56, BATCH_57, BATCH_58, BATCH_59, BATCH_60, BATCH_61, BATCH_62, BATCH_63, BATCH_64, BATCH_65, BATCH_66, BATCH_67}]
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
        self.assertEqual(apply_recorded_repairs(accepted), {(row["char"], row["jyutping"], row["code"], row["evidence"]) for row in batch})
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
        self.assertEqual(apply_recorded_repairs({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"}),
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
                         ("家具行", "gaa1 geoi6 hong4"), ("停刊處分", "ting4 hon1 cyu2 fan1"),
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
        self.assertEqual(apply_recorded_repairs({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"}),
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

    def test_forty_fourth_batch_checks_supported_variants_and_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_44}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_44}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 44), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 307)
        batch = [r for r in curated if r.get("batch") == BATCH_44]
        self.assertEqual(len(batch), 715)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        all_pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in curated}
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("有接縫", "jau5 zip3 fung4", "jau5 zip3 fung6"),
                                         ("杳無影蹤", "miu5 mou4 jing2 zung1", "jiu2 mou4 jing2 zung1")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(all_pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        # Preferred readings already covered by another source stay covered there.
        for word, jp in [("扳機", "baan1 gei1")]:
            self.assertEqual(ranks[word, jp], "常用")
        self.assertEqual(ranks["枕戈待旦", "zam2 gwo1 doi6 daan3"], "預設")
        self.assertEqual(ranks["枕戈待旦", "zam3 gwo1 doi6 daan3"], "常用")
        self.assertEqual(ranks["大海撈針", "daai6 hoi2 lou4 zam1"], "罕見")
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        for pair in [("校友會", "haau6 jau5 wui2"), ("架上來", "gaa3 soeng5 loi4"),
                     ("枕着", "zam3 zoek6"), ("木托盤", "muk6 tok3 pun2")]:
            self.assertIn(pair, pairs)
        self.assertNotIn(("校友會", "haau6 jau5 wui5"), pairs)
        self.assertNotIn(("架空電纜", "gaa3 hung1 din6 laam5"), pairs)
        rejected = {r["char"]: r for r in review if r["verdict"] == "reject"}
        for word, boundary in [("果心", "如果／心聲"), ("服到", "馴服／到"), ("朵花", "一朵花")]:
            self.assertIn(boundary, rejected[word]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", rejected[word]["reading_reference"])
        for bad, good in [("木傢俱", "木家具"), ("木製傢俱", "木製家具"), ("木託盤", "木托盤")]:
            for literal in (bad, good):
                self.assertEqual(to_traditional(literal), good)
                self.assertEqual(to_traditional(to_traditional(literal)), good)
        for literal in ("託付", "委託", "俱樂部"):
            self.assertEqual(to_traditional(literal), literal)

    def test_forty_fifth_batch_preserves_contextual_variants_and_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_45}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_45}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 45), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["net_familiarity_withdrawals"], 301)
        batch = [r for r in curated if r.get("batch") == BATCH_45]
        self.assertEqual(len(batch), 700)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("桌面版", "coek3 min2 baan2", "coek3 min6 baan2"),
                                         ("梳攏", "so1 lung5", "so1 lung4"),
                                         ("簷前", "sim4 cin4", "jim4 cin4"),
                                         ("橋墩下", "kiu4 dan2 haa6", "kiu4 dan1 haa6"),
                                         ("檔案夾", "dong3 on3 gaap2", "dong3 on3 gaap3"),
                                         ("檢查一下", "gim2 caa4 jat1 haa5", "gim2 caa4 jat1 haa6"),
                                         ("校驗文件", "gaau3 jim6 man4 gin2", "gaau3 jim6 man4 gin6")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        for pair in [("極差", "gik6 caa1"), ("機械系統", "gei1 haai6 hai6 tung2"),
                     ("模擬考", "mou4 ji5 haau2"), ("機車行", "gei1 ce1 hong4"),
                     ("檸檬糖", "ning4 mung1 tong2")]:
            self.assertIn(pair, pairs)
        self.assertNotIn(("極差", "gik6 caa3"), pairs)
        self.assertNotIn(("模擬考", "mou4 ji4 haau2"), pairs)
        self.assertEqual(ranks["鱗次櫛比", "leon4 ci3 zit3 bei6"], "常用")
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["85511"]["verdict"], "reject")
        for identifier, boundary in [("85511", "穿梭機／先進"), ("84809", "極／不幸"), ("84929", "大概／不")]:
            self.assertIn(boundary, by_id[identifier]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for literal in ("機械系統", "機械繫統", "机械系统"):
            self.assertEqual(to_traditional(literal), "機械系統")
            self.assertEqual(to_traditional(to_traditional(literal)), "機械系統")
        for literal in ("機械系", "系統", "聯繫", "繫住"):
            self.assertEqual(to_traditional(literal), literal)

    def test_forty_sixth_batch_keeps_modern_readings_and_checks_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_46}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_46}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 46), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 1)
        batch = [r for r in curated if r.get("batch") == BATCH_46]
        self.assertEqual(len(batch), 1070)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(r["char"], r["jyutping"]) for r in batch}
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("正當理由", "zing3 dong3 lei5 jau4", "zing3 dong1 lei5 jau4"),
                                         ("歌友會", "go1 jau5 wui2", "go1 jau5 wui6"),
                                         ("每間房", "mui5 gaan1 fong2", "mui5 gaan1 fong4"),
                                         ("母女倆", "mou5 neoi5 loeng5", "mou5 neoi2 loeng5"),
                                         ("毛氈墊", "mou4 zin1 zin3", "mou4 zin1 din3"),
                                         ("死鏈接", "sei2 lin2 zip3", "sei2 lin6 zip3")]:
            self.assertTrue({(word, preferred), (word, variant)}.issubset(pairs))
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        for pair in [("每頁行數", "mui5 jip6 hong4 sou3"),
                     ("民族樂派", "man4 zuk6 ngok6 paai3"),
                     ("殺病毒", "saat3 beng6 duk6"),
                     ("氈呢", "zin1 nei4"),
                     ("橡膠墊", "zoeng6 gaau1 zin3")]:
            self.assertIn(pair, pairs)
        self.assertEqual(ranks["橡膠墊", "zoeng6 gaau1 din3"], "預設")
        self.assertEqual(ranks["橡膠墊", "zoeng6 gaau1 zin3"], "預設")
        self.assertNotIn(("每頁行數", "mui5 jip6 haang4 sou2"), pairs)
        self.assertNotIn(("民族樂派", "man4 zuk6 lok6 paai3"), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["86503"]["verdict"], "accept")
        self.assertEqual(by_id["87815"]["verdict"], "reject")
        for identifier, boundary in [("86503", "櫻花正開"), ("87815", "大氣層"), ("86259", "悲歡／愛恨")]:
            self.assertIn(boundary, by_id[identifier]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])

    def test_forty_seventh_batch_distinguishes_word_senses_and_lyric_substrings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_47}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_47}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 47), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 9)
        batch = [r for r in curated if r.get("batch") == BATCH_47]
        self.assertEqual(len(batch), 1225)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for word, jp in [("水中毒", "seoi2 zung3 duk6"), ("水分子", "seoi2 fan1 zi2"),
                         ("水分平衡", "seoi2 fan6 ping4 hang4"), ("水煙斗", "seoi2 jin1 dau2"),
                         ("沖泡式", "cung1 paau3 sik1"), ("泡沫劑", "pou5 mut6 zai1"),
                         ("沙發墊", "saa1 faat3 zin3"), ("油量", "jau4 loeng6"),
                         ("治喪委員", "zi6 song3 wai2 jyun4"), ("泳將", "wing6 zoeng3")]:
            self.assertIn((word, jp), pairs)
        for word, jp in [("水中毒", "seoi2 zung1 duk6"), ("水分子", "seoi2 fan6 zi2"),
                         ("水煙斗", "seoi2 jin1 dau3"), ("沖泡式", "cung1 pou5 sik1")]:
            self.assertNotIn((word, jp), pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("水利會", "seoi2 lei6 wui2", "seoi2 lei6 wui6"),
                                         ("沉溺在", "cam4 nik1 zoi6", "cam4 nik6 zoi6"),
                                         ("汞合金", "hung6 hap6 gam1", "hung3 hap6 gam1")]:
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        by_id = {r["id"]: r for r in review}
        for identifier in ("89253", "89580", "89951"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        for identifier, boundary in [("89114", "銀河／上"), ("88834", "沒／傳奇"), ("88423", "求求其其")]:
            self.assertIn(boundary, by_id[identifier]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for literal in ("水烟斗", "水煙斗", "水煙鬥"):
            self.assertEqual(to_traditional(literal), "水煙斗")
            self.assertEqual(to_traditional(to_traditional(literal)), "水煙斗")
        for literal in ("烟斗", "煙斗", "煙鬥"):
            self.assertEqual(to_traditional(literal), "煙斗")
            self.assertEqual(to_traditional(to_traditional(literal)), "煙斗")
        for literal in ("鬥爭", "戰鬥", "北斗", "煙斗"):
            self.assertEqual(to_traditional(literal), literal)
        # Stored group keys also feed the browser's static thesaurus builder.
        for source in ("data/cilin/new_cilin.txt", "data/thesaurus/dict_synonym.txt"):
            group = next(line.split()[1:] for line in (ROOT / source).read_text(encoding="utf-8").splitlines()
                         if line.startswith("Bo32B03= "))
            self.assertEqual(set(group), {"水煙筒", "水煙斗", "水菸袋"})

    def test_forty_eighth_batch_rechecks_corrected_characters_and_modern_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_48}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_48}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 48), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 23)
        batch = [r for r in curated if r.get("batch") == BATCH_48]
        self.assertEqual(len(batch), 1265)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in curated}
        for word, jp in [("派人參加", "paai3 jan4 caam1 gaa1"), ("浩浩湯湯", "hou6 hou6 soeng1 soeng1"),
                         ("淡藍色", "taam5 laam4 sik1"),
                         ("温書假", "wan1 syu1 gaa3"), ("湧上來", "jung2 soeng5 loi4"),
                         ("渲染器", "hyun1 jim5 hei3"),
                         ("渲染器", "syun3 jim5 hei3"), ("深銘肺腑", "sam1 ming5 fai3 fu2"),
                         ("深銘肺腑", "sam1 ming4 fai3 fu2")]:
            self.assertIn((word, jp), pairs)
        for word, jp in [("淡藍色", "taam5 laan4 sik1"), ("奄奄一息", "jim2 jim2 jat1 sik1"),
                         ("温書假", "wan1 syu1 gaa2"), ("構造", "kau1 zou6"),
                         ("浩浩湯湯", "hou6 hou6 tong1 tong1")]:
            self.assertNotIn((word, jp), pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for word, preferred, variant in [("流動比率", "lau4 dung6 bei2 leot2", "lau4 dung6 bei2 leot6"),
                                         ("活頁夾", "wut6 jip6 gaap2", "wut6 jip6 gaap3"),
                                         ("湮滅證據", "jan1 mit6 zing3 geoi3", "jin1 mit6 zing3 geoi3")]:
            self.assertEqual(ranks[word, preferred], "預設")
            self.assertEqual(ranks[word, variant], "常用")
        by_id = {r["id"]: r for r in review}
        for identifier, jp in [("91222", "jim1 jim1 jat1 sik1"), ("91894", "kau3 zou6")]:
            self.assertEqual(by_id[identifier]["verdict"], "already_present")
            self.assertIn(jp, by_id[identifier]["note"])
        for identifier in ("91028", "90500", "91874", "91162"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        for identifier, boundary in [("90003", "快活／到"), ("90500", "大海／會"), ("91028", "深呼吸")]:
            self.assertIn(boundary, by_id[identifier]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for canonical, inputs in [("准建證", ("准建證", "准建证", "準建證")),
                                  ("准遷證", ("准遷證", "准迁证", "準遷證")),
                                  ("游來", ("游來", "游来")),
                                  ("游來游去", ("游來游去", "游来游去")),
                                  ("游進去", ("游進去", "游进去")),
                                  ("游過來", ("游過來", "游过来")),
                                  ("游過去", ("游過去", "游过去"))]:
            for literal in inputs:
                self.assertEqual(to_traditional(literal), canonical)
                self.assertEqual(to_traditional(to_traditional(literal)), canonical)
        for literal in ("遊來", "遊來遊去", "遊進去", "遊過來", "遊過去", "準確", "準備"):
            self.assertEqual(to_traditional(literal), literal)

    def test_forty_ninth_batch_keeps_modern_variants_and_rechecks_corrected_characters(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_49}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_49}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 49), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 57)
        batch = [r for r in curated if r.get("batch") == BATCH_49]
        self.assertEqual(len(batch), 1404)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        for identifier, literal, jp in [("92297", "滿腔熱忱", "mun5 hong1 jit6 sam4"),
                                         ("92443", "漏行", "lau6 hong4"), ("92457", "露面", "lou6 min6"),
                                         ("92562", "瞞天過海", "mun4 tin1 gwo3 hoi2"),
                                         ("92753", "潛滋暗長", "cim4 zi1 am3 zoeng2"),
                                         ("93082", "濾斗", "leoi6 dau2"), ("93095", "洩氣", "sit3 hei3"),
                                         ("93222", "火花塞", "fo2 faa1 sak1"),
                                         ("93778", "無印痕", "mou4 jan3 han4"),
                                         ("93863", "無彈性", "mou4 taan4 sing3"),
                                         ("93974", "無花果樹", "mou4 faa1 gwo2 syu6")]:
            recorded = next(r for r in review if r["id"] == identifier)
            self.assertEqual(to_traditional(recorded["char"]), literal)
            if recorded["verdict"] == "already_present":
                self.assertIn(jp, recorded["note"])
            else:
                self.assertEqual(recorded["verdict"], "accept")
                self.assertEqual(recorded["jyutping"], jp)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for literal, preferred, variant in [("潮聲", "ciu4 seng1", "ciu4 sing1"),
                                            ("焊上", "hon6 soeng5", "hon2 soeng5"),
                                            ("炮烙之刑", "paau3 lok3 zi1 jing4", "paau4 lok3 zi1 jing4")]:
            self.assertEqual(ranks[literal, preferred], "預設")
            self.assertEqual(ranks[literal, variant], "常用")
        self.assertEqual(ranks["烘焙", "hung3 pui4"], "常用")
        self.assertEqual(ranks["滋事分子", "zi1 si6 fan6 zi2"], "預設")
        wrong = LexiconCandidate("滋事分子", "zi1 si6 fan1 zi2", get_0243_code("zi1 si6 fan1 zi2"), ("fixture",))
        retained = [LexiconCandidate(literal, jp, get_0243_code(jp), ("fixture",)) for literal, jp in
                    [("滋事分子", "zi1 si6 fan6 zi2"), ("分子", "fan1 zi2"), ("水分子", "seoi2 fan1 zi2")]]
        self.assertEqual(apply_lexicon_overlay([wrong, *retained], load_corrections()), retained)
        existing_review = ROOT / meta["existing_reading_review_path"]
        self.assertEqual(hashlib.sha256(existing_review.read_bytes()).hexdigest(), meta["existing_reading_review_sha256"])
        self.assertEqual(meta["existing_reading_overlay_deletions"], 1)
        by_id = {r["id"]: r for r in review}
        for identifier in ("93336", "93353", "93445", "93650", "93979"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        for identifier, boundary in [("92308", "沾滿／血垢"), ("92827", "高潮／起跌"),
                                     ("93085", "傾瀉／下來"), ("93740", "無休止")]:
            self.assertIn(boundary, by_id[identifier]["note"])
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for literal in ("濾斗", "滤斗", "濾鬥"):
            self.assertEqual(to_traditional(literal), "濾斗")
            self.assertEqual(to_traditional(to_traditional(literal)), "濾斗")
        for literal in ("潛游", "潜游"):
            self.assertEqual(to_traditional(literal), "潛游")
        self.assertEqual(to_traditional("潛遊"), "潛遊")
        self.assertEqual(to_traditional("鬥爭"), "鬥爭")
        for source in ("data/cilin/new_cilin.txt", "data/thesaurus/dict_synonym.txt"):
            group = next(line.split()[1:] for line in (ROOT / source).read_text(encoding="utf-8").splitlines()
                         if line.startswith("Bo08A06= "))
            self.assertEqual(set(group), {"漏子", "漏斗", "濾斗"})

    def test_fiftieth_batch_aligns_corrected_characters_and_whole_word_preferences(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_50}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_50}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 50), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 193)
        batch = [r for r in curated if r.get("batch") == BATCH_50]
        self.assertEqual(len(batch), 1244)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for pair in [("無限量", "mou4 haan6 loeng6"), ("煤氣中毒", "mui4 hei3 zung3 duk6"),
                     ("熱情好客", "jit6 cing4 hou3 haak3"), ("爺爺奶奶", "je4 je4 naai4 naai2"),
                     ("煮茗", "zyu2 ming5"), ("煮茗", "zyu2 ming4"),
                     ("牛腱", "ngau4 zin2"), ("牛腱", "ngau4 gin3"),
                     ("牛頓定律", "ngau4 deon1 ding6 leot6"), ("牛頓定律", "ngau4 deon6 ding6 leot6"),
                     ("特賣會", "dak6 maai6 wui2"), ("特賣會", "dak6 maai6 wui6")]:
            self.assertIn(pair, pairs)
        for pair in [("物極必反", "mat6 gau3 bit1 faan2"), ("煮豆燃萁", "zyu2 dau6 jin4 gei1"),
                     ("爺爺奶奶", "je4 je4 naai5 naai5"), ("特賣會", "dak6 maai6 wui5")]:
            self.assertNotIn(pair, pairs)
        by_id = {r["id"]: r for r in review}
        for identifier, jp in [("94198", "mou4 gei3 ming4"), ("95769", "mat6 gik6 bit1 faan2"),
                               ("94673", "zyu2 dau6 jin4 kei4")]:
            self.assertEqual(by_id[identifier]["verdict"], "already_present")
            self.assertIn(jp, by_id[identifier]["note"])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["煮茗", "zyu2 ming5"], "預設")
        self.assertEqual(ranks["煮茗", "zyu2 ming4"], "常用")
        self.assertEqual(ranks["無理要求", "mou4 lei5 jiu1 kau4"], "預設")
        self.assertEqual(ranks["燕語呢喃", "jin3 jyu5 nei4 naam4"], "預設")
        self.assertIn("閃照／過後", by_id["94620"]["note"])
        for identifier in ("94338", "94620", "95352", "95459", "95490"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for expected, variants in [("煙斗架", ("煙斗架", "煙鬥架", "烟斗架")),
                                   ("煙斗絲", ("煙斗絲", "煙鬥絲", "烟斗丝"))]:
            for literal in variants:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        self.assertEqual(to_traditional("鬥爭"), "鬥爭")

    def test_fifty_first_batch_checks_word_senses_and_rejects_corpus_fragments(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_51}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_51}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 51), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 676)
        batch = [r for r in curated if r.get("batch") == BATCH_51]
        self.assertEqual(len(batch), 887)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("現貨價格", "jin6 fo3 gaa3 gaak3"), ("現金流量", "jin6 gam1 lau4 loeng6"),
                            ("球場上", "kau4 coeng4 soeng6"), ("猥褻行為", "wai2 sit3 hang4 wai4"),
                            ("猥褻行為", "wui1 sit3 hang4 wai4"), ("玩轉", "waan2 zyun3"),
                            ("玩轉", "waan2 zyun2"), ("瑰異", "gwai1 ji6"),
                            ("瓦楞紙板", "ngaa5 ling4 zi2 baan2"), ("生津解渴", "sang1 zeon1 gaai2 hot3"),
                            ("產科病房", "caan2 fo1 beng6 fong2"), ("產科病房", "caan2 fo1 beng6 fong4")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for pair in [("獲益匪淺", "wok6 jik1 fei1 cin2"), ("狐假虎威", "wu4 ze3 fu2 wai1"),
                     ("狐狸精", "wu4 sing1 zing1"), ("現金流量", "jin6 gam1 lau4 loeng4")]:
            self.assertNotIn(pair, pairs)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["96706"]["verdict"], "already_present")
        self.assertIn("wok6 jik1 fei2 cin2", by_id["96706"]["note"])
        for identifier in ("96652", "97396", "97456", "97481", "97822", "97867"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        self.assertIn("來生／相愛", by_id["97822"]["note"])
        for identifier in ("96215", "96372", "96482", "96597", "96619", "97167", "97623", "97822", "97830"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for pair in [("狂風怒號", "kwong4 fung1 nou6 hou4"), ("玄奧晦澀", "jyun4 ou3 fui3 sap1"),
                     ("產科病房", "caan2 fo1 beng6 fong2")]:
            self.assertEqual(ranks[pair], "預設")
        self.assertEqual(ranks["產科病房", "caan2 fo1 beng6 fong4"], "常用")

    def test_fifty_second_batch_distinguishes_motion_and_container_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_52}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_52}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 52), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 357)
        self.assertEqual(meta["unreviewed_pool_candidates"], 46608)
        batch = [r for r in curated if r.get("batch") == BATCH_52]
        self.assertEqual(len(batch), 983)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("甩乾", "seot1 gon1"), ("甩膠", "lat1 gaau1"),
                            ("甲乙", "gaap3 jyut3"), ("甲乙", "gaap3 jyut6"),
                            ("男生宿舍", "naam4 sang1 suk1 se3"), ("當一回事", "dong3 jat1 wui4 si6"),
                            ("病入骨髓", "beng6 jap6 gwat1 seoi5"), ("痛惡", "tung3 wu3"),
                            ("痛愛", "tung3 oi3"), ("發完", "faat3 jyun4"),
                            ("發帖數", "faat3 tip3 sou3"), ("白淨淨", "baak6 zeng6 zeng6"),
                            ("發酵劑", "faat3 haau1 zai1"), ("發酵劑", "faat3 gaau3 zai1"),
                            ("盛菜", "sing4 coi3"), ("盛菜", "sing6 coi3")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for pair in [("甩乾", "lat1 gon1"), ("當一回事", "dong1 jat1 wui4 si6"),
                     ("白癜風", "baak6 din1 fung1"), ("痛惡", "tung3 ok3")]:
            self.assertNotIn(pair, pairs)
        by_id = {r["id"]: r for r in review}
        for identifier in ("98319", "98657", "98662", "98888", "99169", "99283", "99537", "99548", "99579", "99745"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        self.assertIn("蒸發掉", by_id["99283"]["note"])
        self.assertIn("明白／血肉", by_id["99537"]["note"])
        for identifier in ("98319", "98431", "98566", "98662", "98975", "99169", "99244", "99283", "99537"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["盛菜", "sing4 coi3"], "預設")
        self.assertEqual(ranks["盛菜", "sing6 coi3"], "常用")
        self.assertEqual(ranks["白淨淨", "baak6 zeng6 zeng6"], "預設")
        self.assertEqual(ranks["甲乙", "gaap3 jyut6"], "預設")
        self.assertEqual(ranks["甲乙", "gaap3 jyut3"], "常用")

    def test_fifty_third_batch_preserves_modern_readings_and_exact_word_senses(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_53}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_53}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 53), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 441)
        self.assertEqual(meta["unreviewed_pool_candidates"], 44608)
        batch = [r for r in curated if r.get("batch") == BATCH_53]
        self.assertEqual(len(batch), 908)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("盡其所長", "zeon6 kei4 so2 coeng4"), ("相距千里", "soeng1 keoi5 cin1 leoi5"),
                            ("相隔萬里", "soeng1 gaak3 maan6 leoi5"), ("直面人生", "zik6 min6 jan4 sang1"),
                            ("監聽室", "gaam1 teng1 sat1"), ("監聽室", "gaam1 ting1 sat1"),
                            ("着上", "zoek3 soeng5"), ("睜開眼", "zaang1 hoi1 ngaan5"),
                            ("睜開眼", "zang1 hoi1 ngaan5"), ("睫毛液", "zit3 mou4 jik6"),
                            ("睫毛液", "zit6 mou4 jik6"), ("真菌病", "zan1 kwan2 beng6"),
                            ("破曉時分", "po3 hiu2 si4 fan1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("盡其所長", "zeon6 kei4 so2 zoeng2"), ("監聽室", "gaam1 ting3 sat1"),
                            ("真菌病", "zan1 kwan2 bing6")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        for identifier in ("100541", "100640", "100825", "100866", "101133", "101297", "101638", "101757", "101772"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        for identifier, literal in [("100541", "相樸"), ("100640", "盾狀腺"), ("100825", "真信實意"),
                                    ("101297", "瞑思苦想"), ("101638", "矮杆")]:
            self.assertEqual(by_id[identifier]["char"], literal)
        self.assertIn("天真／得", by_id["100866"]["note"])
        self.assertIn("白石／畫下", by_id["101757"]["note"])
        self.assertIn("迎着／上", by_id["101125"]["note"])
        for identifier in ("100002", "100019", "100608", "100755", "100866", "101125", "101133", "101169", "101191", "101302", "101757"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["睫毛液", "zit3 mou4 jik6"], "預設")
        self.assertEqual(ranks["睫毛液", "zit6 mou4 jik6"], "常用")
        self.assertEqual(ranks["假睫毛", "gaa2 zit3 mou4"], "預設")
        for expected, inputs in [("直面人生", ("直面人生", "直麪人生")),
                                 ("相隔萬里", ("相隔万里", "相隔萬里", "相隔萬裏"))]:
            for literal in inputs:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        self.assertEqual(to_traditional("麪粉"), "麪粉")
        self.assertEqual(to_traditional("裏外"), "裏外")

    def test_fifty_fourth_batch_repairs_response_readings_and_preserves_modern_variants(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_54}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_54}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 54), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 56)
        self.assertEqual(meta["unreviewed_pool_candidates"], 42608)
        batch = [r for r in curated if r.get("batch") == BATCH_54]
        self.assertEqual(len(batch), 1000)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in curated}
        for literal, jp in [("積極響應", "zik1 gik6 hoeng2 jing3"), ("響應者", "hoeng2 jing3 ze2"),
                            ("私家轎車", "si1 gaa1 giu2 ce1"), ("私家轎車", "si1 gaa1 giu6 ce1"),
                            ("私家轎車", "si1 gaa1 kiu2 ce1"), ("磨到", "mo4 dou3"), ("磨到", "mo4 dou2"),
                            ("種因", "zung3 jan1"), ("種過", "zung3 gwo3"), ("磅稱", "bong6 cing3"),
                            ("豌豆", "wun2 dau6"), ("豌豆", "wun1 dau6"), ("碌碌無聞", "luk1 luk1 mou4 man4"),
                            ("私放罪犯", "si1 fong3 zeoi6 faan2"), ("私放罪犯", "si1 fong3 zeoi6 faan6"),
                            ("積累資金", "zik1 leoi6 zi1 gam1"), ("積累資金", "zik1 leoi5 zi1 gam1"),
                            ("科學論斷", "fo1 hok6 leon6 dyun3"), ("祛病健身", "keoi1 beng6 gin6 san1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        self.assertNotIn(("響應者", "hoeng2 jing1 ze2"), pairs)
        repaired = [r for r in review if r["verdict"] == "repair"]
        self.assertEqual([(r["id"], r["char"], r["previous_jyutping"]) for r in repaired], [("21696", "響應者", "hoeng2 jing1 ze2")])
        responder = next(r for r in curated if r["char"] == "響應者")
        self.assertEqual(responder["batch"], BATCH_13)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["103235"]["verdict"], "reject")
        self.assertIn("自私／地", by_id["103235"]["note"])
        for identifier in ("102308", "102500", "103235", "103571", "103834"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["響應者", "hoeng2 jing3 ze2"], "預設")
        self.assertEqual(ranks["私家轎車", "si1 gaa1 giu2 ce1"], "預設")
        self.assertEqual(ranks["私家轎車", "si1 gaa1 kiu2 ce1"], "常用")
        for expected, inputs in [("移星換斗", ("移星换斗", "移星換斗", "移星換鬥")),
                                 ("礙難照准", ("碍难照准", "礙難照准", "礙難照準"))]:
            for literal in inputs:
                self.assertEqual(to_traditional(literal), expected)
                self.assertEqual(to_traditional(to_traditional(literal)), expected)
        self.assertEqual(to_traditional("鬥爭"), "鬥爭")
        self.assertEqual(to_traditional("標準"), "標準")
        originals = [("響應", "hoeng2 jing1"), ("響應", "hoeng2 jing3"),
                     ("轎車", "kiu4 ce1"), ("轎車", "giu2 ce1"), ("轎車", "giu6 ce1"), ("轎車", "kiu2 ce1"),
                     ("轎", "kiu4"), ("響應時間", "hoeng2 jing3 si4 gaan3"), ("累積", "leoi6 zik1")]
        candidates = [LexiconCandidate(char=c, jyutping=j, code=get_0243_code(j), sources=("fixture",)) for c, j in originals]
        kept = {(r.char, r.jyutping) for r in apply_lexicon_overlay(candidates, load_corrections(CURATED.with_name("lexicon_corrections.tsv")))}
        self.assertEqual(kept, set(originals) - {("響應", "hoeng2 jing1"), ("轎車", "kiu4 ce1")})

    def test_fifty_fifth_batch_preserves_fixed_words_and_distinguishes_sticky_senses(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_55}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_55}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 55), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 188)
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 40608)
        batch = [r for r in curated if r.get("batch") == BATCH_55]
        self.assertEqual(len(batch), 1094)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("穩定上升", "wan2 ding6 soeng6 sing1"), ("穩定上升", "wan2 ding6 soeng5 sing1"),
                            ("空中加油", "hung1 zung1 gaa1 jau2"), ("空中加油", "hung1 zung1 gaa1 jau4"),
                            ("籠罩着", "lung5 zaau3 zoek6"), ("籠罩着", "lung4 zaau3 zoek6"),
                            ("競選活動", "ging6 syun2 wut6 dung6"), ("競選活動", "ging3 syun2 wut6 dung6"),
                            ("粘住", "nim4 zyu6"), ("粘住", "zim1 zyu6"), ("粘結性", "nim1 git3 sing3"),
                            ("管理局長", "gun2 lei5 guk6 zoeng2"), ("籌備會議", "cau4 bei6 wui6 ji5"),
                            ("答謝會", "daap3 ze6 wui2"), ("答辯會", "daap3 bin6 wui2"),
                            ("節數", "zit3 sou3"), ("篇數", "pin1 sou3"), ("篤學好古", "duk1 hok6 hou3 gu2"),
                            ("穿起", "cyun1 hei2"), ("窄路", "zaak3 lou6"), ("童話般", "tung4 waa2 bun1"),
                            ("竹杆", "zuk1 gon1"), ("窗簾桿", "coeng1 lim2 gon2"), ("窗簾桿", "coeng1 lim2 gon1"),
                            ("粗花呢", "cou1 faa1 nei4"), ("粒粒", "nap1 nap1"), ("粒粒", "lap1 lap1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("穿起", "cyun1 hei1"), ("窄路", "zaak3 lou3"), ("管理局長", "gun2 lei5 guk6 coeng4"),
                            ("籌備會議", "cau4 bei6 wui2 ji5"), ("答謝會", "daap3 ze6 wui5"),
                            ("篇數", "pin1 sou2"), ("篤學好古", "duk1 hok6 hou2 gu2")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertIn("無窮／氣數", by_id["104548"]["note"])
        self.assertIn("季節／會", by_id["105394"]["note"])
        for identifier in ("104214", "104350", "104432", "104548", "104691", "104754", "105076", "105227", "105394", "105463", "105691"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for identifier in ("104013", "104513", "105190", "105461", "105925"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        self.assertEqual(by_id["105190"]["char"], "箇中人")
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for literal, jp in [("空中加油", "hung1 zung1 gaa1 jau2"), ("籠罩着", "lung5 zaau3 zoek6"),
                            ("竹簾子", "zuk1 lim4 zi2"), ("粗花呢", "cou1 faa1 nei4"), ("算得什麼", "syun3 dak1 sam6 mo1")]:
            self.assertEqual(ranks[literal, jp], "預設")
        self.assertEqual(ranks["籠罩着", "lung4 zaau3 zoek6"], "常用")
        self.assertEqual(ranks["競選活動", "ging3 syun2 wut6 dung6"], "常用")

    def test_fifty_sixth_batch_keeps_whole_word_senses_and_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_56}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_56}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 56), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 154)
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 38608)
        batch = [r for r in curated if r.get("batch") == BATCH_56]
        self.assertEqual(len(batch), 1105)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("紀律處分", "gei2 leot6 cyu2 fan1"), ("紀律處分", "gei2 leot6 cyu5 fan1"),
                            ("紀錄下來", "gei3 luk6 haa6 loi4"), ("紀錄下來", "gei2 luk6 haa6 loi4"),
                            ("系統診斷", "hai6 tung2 can2 dyun3"), ("系統診斷", "hai6 tung2 can2 dyun6"),
                            ("級長", "kap1 zoeng2"), ("紙縫", "zi2 fung6"), ("紙縫", "zi2 fung4"),
                            ("素負盛名", "sou3 fu6 sing6 ming4"), ("純音樂", "seon4 jam1 ngok6"),
                            ("統計權重", "tung2 gai3 kyun4 cung5"), ("緝拿罪犯", "cap1 naa4 zeoi6 faan2"),
                            ("緊接著", "gan2 zip3 zoek6"), ("緣分已盡", "jyun4 fan6 ji5 zeon6"),
                            ("累得", "leoi6 dak1"), ("細數", "sai3 sou2"), ("終必", "zung1 bit1"),
                            ("終會", "zung1 wui5"), ("終有", "zung1 jau5"),
                            ("絲綿被", "si1 min4 pei5"), ("緞被", "dyun6 pei5"),
                            ("絨線刺繡", "jung2 sin3 ci3 sau3"), ("絨線刺繡", "jung4 sin3 ci3 sau3")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("紀律處分", "gei2 leot6 cyu2 fan6"), ("級長", "kap1 coeng4"),
                            ("紙縫", "zi2 laa3"), ("素負盛名", "sou3 fu6 sing4 ming4"),
                            ("緊接著", "gan2 zip3 zyu3"), ("緣分已盡", "jyun4 fan1 ji5 zeon6"),
                            ("絲綿被", "si1 min4 bei6"), ("緞被", "dyun6 bei6")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertIn("始終／會", by_id["106833"]["note"])
        self.assertIn("始終／有", by_id["106834"]["note"])
        self.assertIn("給你／愛護過", by_id["107149"]["note"])
        for identifier in ("106707", "106756", "106827", "106833", "106834", "107149"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for identifier in ("106048", "106121", "106271", "106419", "106481", "107149", "107755", "107986"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["紀錄下來", "gei3 luk6 haa6 loi4"], "預設")
        self.assertEqual(ranks["紀錄下來", "gei2 luk6 haa6 loi4"], "常用")
        self.assertEqual(ranks["綠葉成蔭", "luk6 jip6 sing4 jam1"], "預設")

    def test_fifty_seventh_batch_distinguishes_direction_and_preserves_modern_variants(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_57}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_57}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 57), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 242)
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 36608)
        batch = [r for r in curated if r.get("batch") == BATCH_57]
        self.assertEqual(len(batch), 1073)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("緩慢行走", "wun6 maan6 haang4 zau2"), ("緩慢行走", "wun4 maan6 haang4 zau2"),
                            ("縱向設計", "zung1 hoeng3 cit3 gai3"), ("縱情歌唱", "zung3 cing4 go1 coeng3"),
                            ("總重", "zung2 cung5"), ("總重", "zung2 zung6"), ("總長度", "zung2 coeng4 dou6"),
                            ("總該會", "zung2 goi1 wui5"), ("考中", "haau2 zung3"), ("考校", "haau2 gaau3"),
                            ("繫鞋帶", "gai3 haai2 daai2"), ("繫鞋帶", "hai6 haai2 daai2"),
                            ("繩橋", "sing2 kiu4"), ("繩橋", "sing4 kiu4"),
                            ("繞過去", "jiu2 gwo3 heoi3"), ("繞過去", "jiu5 gwo3 heoi3"),
                            ("翹起來", "kiu3 hei2 loi4"), ("翹起來", "kiu4 hei2 loi4"),
                            ("群英薈萃", "kwan4 jing1 kui2 seoi6"), ("群英薈萃", "kwan4 jing1 wui6 seoi6"),
                            ("群英薈萃", "kwan4 jing1 wai3 seoi6"), ("縫釦子", "fung4 kau3 zi2"),
                            ("聚會地點", "zeoi6 wui2 dei6 dim2"), ("聚會地點", "zeoi6 wui6 dei6 dim2"),
                            ("聚斂錢財", "zeoi6 lim5 cin2 coi4"), ("聚斂錢財", "zeoi6 lim6 cin2 coi4"),
                            ("續借手續", "zuk6 ze3 sau2 zuk6"), ("老歌", "lou5 go1"), ("置身於", "zi3 san1 jyu1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("總重", "zung2 cung4"), ("總長度", "zung2 zoeng2 dou6"),
                            ("總該會", "zung2 goi1 wui2"), ("考中", "haau2 zung1"),
                            ("群英薈萃", "kwan4 jing1 wai6 seoi6"), ("縫釦子", "fung4 kau2 zi2")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        for raw in ("续借手续", "續借手續", "續藉手續"):
            self.assertEqual(to_traditional(raw), "續借手續")
            self.assertEqual(to_traditional(to_traditional(raw)), "續借手續")
        by_id = {r["id"]: r for r in review}
        self.assertIn("空翻／上落", by_id["109331"]["note"])
        for identifier in ("108017", "108346", "108845", "109331", "109509"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for identifier in ("108060", "108302", "108652", "108661", "109093", "109544"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["緩慢行走", "wun6 maan6 haang4 zau2"], "預設")
        self.assertEqual(ranks["緩慢行走", "wun4 maan6 haang4 zau2"], "常用")
        self.assertEqual(ranks["耐腐蝕性", "noi6 fu6 sik6 sing3"], "預設")

    def test_fifty_eighth_batch_checks_hearing_memorization_and_campaign_senses(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_58}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_58}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 58), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 257)
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 34608)
        batch = [r for r in curated if r.get("batch") == BATCH_58]
        self.assertEqual(len(batch), 968)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("聞起來", "man4 hei2 loi4"), ("聞風響應", "man4 fung1 hoeng2 jing3"),
                            ("聽得見", "teng1 dak1 gin3"), ("聽得見", "ting1 dak1 gin3"),
                            ("聽覺定位", "ting3 gok3 ding6 wai6"), ("聽裝", "ting3 zong1"),
                            ("聽從命令", "teng1 cung4 ming6 ling6"), ("聽從命令", "ting3 cung4 ming6 ling6"),
                            ("背下來", "bui6 haa6 loi4"), ("背下來", "bui3 haa6 loi4"),
                            ("背不動", "bui3 bat1 dung6"), ("背誦課文", "bui6 zung6 fo3 man4"),
                            ("胃粘膜", "wai6 nim1 mok6"), ("胃粘膜", "wai6 nim1 mok2"),
                            ("腸粘連", "coeng4 nim4 lin4"), ("肥分", "fei4 fan6"),
                            ("脂肪粒", "zi1 fong1 nap1"), ("脂肪粒", "zi1 fong1 lap1"),
                            ("能謀善斷", "nang4 mau4 sin6 dyun3"), ("腳上", "goek3 soeng6"),
                            ("臆度", "jik1 dok6"), ("自供狀", "zi6 gung1 zong6"),
                            ("自傳式", "zi6 zyun6 sik1"), ("自彈", "zi6 taan4"),
                            ("自上到下", "zi6 soeng6 dou3 haa6"), ("能征善戰", "nang4 zing1 sin6 zin3"),
                            ("自我欣賞", "zi6 ngo5 jan1 soeng2"), ("膽石病", "daam2 sek6 beng6")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("聽裝", "teng1 zong1"), ("肥分", "fei4 fan1"),
                            ("腳上", "goek3 soeng5"), ("自供狀", "zi6 gung3 zong6"),
                            ("自傳式", "zi6 zyun2 sik1"), ("自彈", "zi6 daan2"),
                            ("臆度", "jik1 dou6"), ("膽石病", "daam2 sek6 bing6")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        for raw in ("能征善战", "能征善戰", "能徵善戰"):
            self.assertEqual(to_traditional(raw), "能征善戰")
            self.assertEqual(to_traditional(to_traditional(raw)), "能征善戰")
        self.assertEqual(to_traditional("徵求"), "徵求")
        by_id = {r["id"]: r for r in review}
        self.assertIn("能／成", by_id["110990"]["note"])
        self.assertIn("才能／開心", by_id["111065"]["note"])
        self.assertIn("心胸／裏", by_id["110952"]["note"])
        self.assertIn("未能／及時", by_id["110974"]["note"])
        for identifier in ("110342", "110660", "110952", "110974", "110990", "111036", "111065", "111123", "111929", "111978"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for identifier in ("110974", "111014", "111123", "111607", "111709", "111829", "111951"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["聽得見", "teng1 dak1 gin3"], "預設")
        self.assertEqual(ranks["聽得見", "ting1 dak1 gin3"], "常用")
        self.assertEqual(ranks["背下來", "bui6 haa6 loi4"], "預設")
        self.assertEqual(ranks["背下來", "bui3 haa6 loi4"], "常用")
        self.assertEqual(ranks["聾啞症", "lung4 ngaa2 zing3"], "預設")
        self.assertEqual(ranks["腸痙攣", "coeng4 ging6 lyun4"], "預設")

    def test_fifty_ninth_batch_distinguishes_word_senses_and_keeps_modern_variants(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_59}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_59}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 59), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 526)
        self.assertEqual(meta["net_familiarity_withdrawals"], 525)
        self.assertEqual(meta["explicit_restored_candidates"], [112129])
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 32608)
        batch = [r for r in curated if r.get("batch") == BATCH_59]
        self.assertEqual(len(batch), 888)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("自由軟件", "zi6 jau4 jyun5 gin2"), ("自種", "zi6 zung3"),
                            ("至死不降", "zi3 sei2 bat1 hong4"), ("興之所至", "hing3 zi1 so2 zi3"),
                            ("興趣愛好", "hing3 ceoi3 oi3 hou3"), ("興頭上", "hing3 tau4 soeng6"),
                            ("與會人士", "jyu6 wui2 jan4 si6"), ("與會人士", "jyu5 wui6 jan4 si6"),
                            ("舀水", "jiu5 seoi2"), ("舀水", "jiu2 seoi2"),
                            ("舉手表決", "geoi2 sau2 biu2 kyut3"), ("舊傢俱", "gau6 gaa1 geoi6"),
                            ("舊創", "gau6 cong1"), ("芒果汁", "mong1 gwo2 zap1"), ("芒果汁", "mong4 gwo2 zap1"),
                            ("芝麻湯圓", "zi1 maa4 tong1 jyun2"), ("英語聽力", "jing1 jyu5 teng1 lik6"),
                            ("茅檐", "maau4 sim4"), ("茅檐", "maau4 jim4"), ("茅檐", "maau4 jam4"),
                            ("茼蒿菜", "tong4 hou1 coi3"), ("茼蒿菜", "tong4 ou1 coi3"), ("茼蒿菜", "tung4 hou1 coi3"),
                            ("自縊身亡", "zi6 ai3 san1 mong4"), ("自縊身亡", "zi6 ngai3 san1 mong4"),
                            ("與子偕老", "jyu5 zi2 haai4 lou5"), ("與子偕老", "jyu5 zi2 gaai1 lou5"),
                            ("莞爾而笑", "wun2 ji5 ji4 siu3"), ("莞爾而笑", "wun5 ji5 ji4 siu3"),
                            ("草地上", "cou2 dei6 soeng6"), ("草草率率", "cou2 cou2 seot1 seot1"),
                            ("荷槍", "ho6 coeng1"), ("落泊", "lok6 bok6"), ("落下來", "lok6 haa6 loi4"),
                            ("著實", "zoek6 sat6"), ("著有", "zyu3 jau5"), ("蒔花種草", "si4 faa1 zung3 cou2"),
                            ("萬貫家私", "maan6 gun3 gaa1 si1"), ("葉面肥", "jip6 min6 fei4")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("至死不降", "zi3 sei2 bat1 gong3"), ("興之所至", "hing1 zi1 so2 zi3"),
                            ("舊傢俱", "gau6 gaa1 keoi1"), ("舊創", "gau6 cong3"),
                            ("草草記錄", "cou2 cou2 gei2 luk6"), ("落泊", "lok6 paak3"),
                            ("落泊", "lok6 pok3"), ("著有", "zoek3 jau5"), ("著實", "zoek3 sat6")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        for expected, inputs in [("舉手表決", ("举手表决", "舉手表決", "舉手錶決")),
                                 ("萬貫家私", ("万贯家私", "萬貫家私", "萬貫傢俬")),
                                 ("葉面肥", ("叶面肥", "葉面肥", "葉麪肥"))]:
            for raw in inputs:
                self.assertEqual(to_traditional(raw), expected)
                self.assertEqual(to_traditional(to_traditional(raw)), expected)
        by_id = {r["id"]: r for r in review}
        for identifier, boundary in [("112471", "一舉／有"), ("112524", "舊／創傷"), ("112976", "紫色／香薰"), ("113218", "若／要是")]:
            self.assertIn(boundary, by_id[identifier]["note"])
        for identifier in ("112035", "112091", "112192", "112242", "112471", "112524", "112533", "112855", "112971", "112976", "113014", "113097", "113217", "113218", "113813", "113859"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for identifier in ("112471", "112435", "112466", "113496", "113714", "113743", "113828", "113907"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["與會人士", "jyu6 wui2 jan4 si6"], "預設")
        self.assertEqual(ranks["與會人士", "jyu5 wui6 jan4 si6"], "常用")
        self.assertEqual(ranks["芒果汁", "mong1 gwo2 zap1"], "預設")
        self.assertEqual(ranks["芒果汁", "mong4 gwo2 zap1"], "常用")
        self.assertEqual(ranks["舊創", "gau6 cong1"], "預設")

    def test_sixtieth_batch_checks_contextual_tones_and_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_60}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_60}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 60), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["second_pass_familiarity_withdrawals"], 318)
        self.assertEqual(meta["explicit_restored_candidates"], [])
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 30608)
        batch = [r for r in curated if r.get("batch") == BATCH_60]
        self.assertEqual(len(batch), 470)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("蒸發掉", "zing1 faat3 diu6"), ("蓮花瓣", "lin4 faa1 faan6"),
                            ("蓮花瓣", "lin4 faa1 baan6"), ("藤傢俱", "tang4 gaa1 geoi6"),
                            ("藤傢俱", "tang4 gaa1 keoi1"), ("藥物中毒", "joek6 mat6 zung3 duk6"),
                            ("藥物製劑", "joek6 mat6 zai3 zai1"), ("處理方式", "cyu2 lei5 fong1 sik1"),
                            ("處理方式", "cyu5 lei5 fong1 sik1"), ("處得來", "cyu2 dak1 loi4"),
                            ("虛心接受", "heoi1 sam1 zip3 sau6"), ("虛擬空間", "heoi1 ji5 hung1 gaan1"),
                            ("虛擬空間", "heoi1 ji4 hung1 gaan1"), ("蠶絲被", "caam4 si1 bei2"),
                            ("蠶絲被", "caam4 si1 bei6"), ("蠶豆病", "caam4 dau2 beng6"),
                            ("血流量", "hyut3 lau4 loeng6"), ("行數", "hong4 sou3"),
                            ("行俠好義", "hang4 hap6 hou3 ji6"), ("行有行規", "hong4 jau5 hong4 kwai1"),
                            ("行行好", "hang4 hang4 hou2"), ("行情看漲", "hong4 cing4 hon3 zoeng3"),
                            ("行情看漲", "hong4 cing4 hon3 zoeng2"), ("衍生品", "jin2 sang1 ban2"),
                            ("衍生品", "hin2 sang1 ban2"), ("衣着打扮", "ji1 zoek3 daa2 baan6"),
                            ("衝到", "cung1 dou3"), ("衝過", "cung1 gwo3"),
                            ("衷心祝福", "cung1 sam1 zuk1 fuk1"), ("被貶", "bei6 bin2"),
                            ("表妹夫", "biu2 mui6 fu1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("藥物中毒", "joek6 mat6 zung1 duk6"), ("藥物製劑", "joek6 mat6 zai3 zai3"),
                            ("處理方式", "cyu3 lei5 fong1 sik1"), ("行數", "haang4 sou2"),
                            ("行俠好義", "haang4 hap6 hou2 ji6"), ("行有行規", "haang4 jau5 hong4 kwai1"),
                            ("行行好", "hong4 hong4 hou2"), ("衣着打扮", "ji1 zoek6 daa2 baan6"),
                            ("衝到", "cung1 dou2"), ("蠶豆病", "caam4 dau2 bing6"),
                            ("表妹夫", "biu2 mui2 fu1")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertIn("相處／到", by_id["114586"]["note"])
        self.assertIn("相處／得", by_id["114595"]["note"])
        for identifier in ("114030", "114586", "114595", "114654", "115595", "115849", "115935"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for identifier in ("114586", "114595", "114077", "114189", "114260", "114285", "115554", "115611", "115955"):
            self.assertEqual(by_id[identifier]["verdict"], "reject")
        self.assertEqual(by_id["114111"]["source_literal"], "蓬头散发")
        self.assertEqual(by_id["114111"]["char"], "蓬頭散髮")
        self.assertEqual(by_id["114111"]["verdict"], "already_present")
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["藤傢俱", "tang4 gaa1 geoi6"], "預設")
        self.assertEqual(ranks["藤傢俱", "tang4 gaa1 keoi1"], "常用")
        self.assertEqual(ranks["虛擬空間", "heoi1 ji5 hung1 gaan1"], "預設")
        self.assertEqual(ranks["虛擬空間", "heoi1 ji4 hung1 gaan1"], "常用")
        self.assertEqual(ranks["行數", "hong4 sou3"], "預設")

    def test_sixty_first_batch_checks_readings_and_exact_existing_repair(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_61}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_61}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 61), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["net_familiarity_withdrawals"], 455)
        self.assertEqual(len(meta["explicit_restored_candidates"]), 248)
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 28608)
        batch = [r for r in curated if r.get("batch") == BATCH_61]
        self.assertEqual(len(batch), 626)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("親善大使", "can1 sin6 daai6 si5"), ("親善大使", "can1 sin6 daai6 si3"),
                            ("親家公", "can3 gaa1 gung1"), ("親家翁", "can3 gaa1 jung1"),
                            ("親口答應", "can1 hau2 daap3 jing3"), ("見精識精", "gin3 zeng1 sik1 zeng1"),
                            ("計量單位", "gai3 loeng4 daan1 wai6"), ("詞彙量", "ci4 wui6 loeng6"),
                            ("詞數", "ci4 sou3"), ("解送犯人", "gaai3 sung3 faan6 jan4"),
                            ("解剖圖", "gaai2 fau2 tou4"), ("解剖圖", "gaai2 pau2 tou4"),
                            ("視聽資料", "si6 ting3 zi1 liu2"), ("視聽資料", "si6 ting1 zi1 liu2"),
                            ("訂機票", "deng6 gei1 piu3"), ("訂機票", "ding3 gei1 piu3"),
                            ("訂機票", "ding6 gei1 piu3"), ("訂正作業", "ding3 zing3 zok3 jip6"),
                            ("訂正作業", "ding6 zing3 zok3 jip6"), ("記錄簿", "gei3 luk6 bou2"),
                            ("記錄簿", "gei3 luk6 bou6"), ("診斷器", "can2 dyun3 hei3"),
                            ("診斷器", "can2 dyun6 hei3"), ("裝病", "zong1 beng6"),
                            ("褶裙", "zip3 kwan4"), ("褶裙", "zaap3 kwan4"),
                            ("褻玩", "sit3 wun6"), ("討工錢", "tou2 gung1 cin2")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("親善大使", "can1 sin6 daai6 sai2"), ("親家公", "can1 gaa1 gung1"),
                            ("計量單位", "gai3 loeng6 daan1 wai6"), ("詞彙量", "ci4 wui6 loeng4"),
                            ("解送犯人", "gaai2 sung3 faan6 jan4"), ("裝病", "zong1 bing6")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        for identifier, boundary in [("116512", "東西／偏遠"), ("116567", "不要／以為"), ("116572", "太重要／使我")]:
            self.assertEqual(by_id[identifier]["verdict"], "reject")
            self.assertIn(boundary, by_id[identifier]["note"])
        for identifier in ("116452", "116512", "116567", "116572", "116573", "116594", "116966", "117104", "117141"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["親善大使", "can1 sin6 daai6 si5"], "預設")
        self.assertEqual(ranks["親善大使", "can1 sin6 daai6 si3"], "常用")
        self.assertEqual(ranks["訂機票", "deng6 gei1 piu3"], "預設")
        self.assertEqual(ranks["訂機票", "ding6 gei1 piu3"], "常用")
        originals = [("行將", "hang6 zoeng1"), ("品行", "ban2 hang6"), ("罪行", "zeoi6 hang6"),
                     ("修行", "sau1 hang6"), ("行將崩潰", "hang4 zoeng1 bang1 kui2"),
                     ("行將滅亡", "haang4 zoeng1 mit6 mong4")]
        candidates = [LexiconCandidate(c, j, get_0243_code(j), ("kaifang",)) for c, j in originals]
        fixed = apply_lexicon_overlay(candidates, load_corrections())
        self.assertEqual({(r.char, r.jyutping) for r in fixed}, set(originals) - {originals[0]} | {("行將", "hang4 zoeng1")})
        self.assertEqual(fixed[0].sources, candidates[0].sources)
        self.assertEqual(fixed[0].code, "03")

    def test_sixty_second_batch_separates_tuning_requests_and_lyric_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_62}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_62}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 62), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["net_familiarity_withdrawals"], 69)
        self.assertEqual(meta["explicit_restored_candidates"], [119662])
        self.assertEqual(meta["unreviewed_pool_candidates"], 26608)
        batch = [r for r in curated if r.get("batch") == BATCH_62]
        self.assertEqual(len(batch), 959)
        self.assertEqual(apply_recorded_repairs({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"}),
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("調高", "tiu4 gou1"), ("調光", "tiu4 gwong1"), ("調琴", "tiu4 kam4"),
                            ("調上", "tiu4 soeng5"), ("調上", "diu6 soeng5"), ("調兵", "diu6 bing1"),
                            ("調配出", "tiu4 pui3 ceot1"), ("調配出", "diu6 pui3 ceot1"),
                            ("請假單", "ceng2 gaa3 daan1"), ("請假單", "cing2 gaa3 daan1"),
                            ("請坐下", "ceng2 co5 haa6"), ("請坐下", "cing2 co5 haa6"),
                            ("請降", "cing2 hong4"), ("誓死不降", "sai6 sei2 bat1 hong4"),
                            ("說唱樂", "syut3 coeng3 ngok6"), ("說短道長", "syut3 dyun2 dou6 coeng4"),
                            ("說服教育", "seoi3 fuk6 gaau3 juk6"), ("話中帶刺", "waa6 zung1 daai3 ci3"),
                            ("話題一轉", "waa6 tai4 jat1 zyun2"), ("詩歌散文", "si1 go1 saan2 man4"),
                            ("誤報率", "ng6 bou3 leot6"), ("謹備菲酌", "gan2 bei6 fei2 zoek3"),
                            ("警察局長", "ging2 caat3 guk6 zoeng2"), ("豎行", "syu6 hong4"),
                            ("語云", "jyu5 wan4"), ("讀過去", "duk6 gwo3 heoi3"),
                            ("變到", "bin3 dou3"), ("講到", "gong2 dou3")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("調高", "diu6 gou1"), ("請假單", "cing2 gaa2 daan1"),
                            ("請降", "cing2 gong3"), ("說唱樂", "syut3 coeng3 lok6"),
                            ("說短道長", "syut3 dyun2 dou6 zoeng2"), ("話中帶刺", "waa6 zung3 daai3 ci3"),
                            ("誤報率", "ng6 bou3 leot2"), ("警察局長", "ging2 caat3 guk6 coeng4"),
                            ("豎行", "syu6 haang4")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["119834"]["verdict"], "reject")
        self.assertIn("改變／過去", by_id["119834"]["note"])
        self.assertIn("白髮", by_id["119779"]["note"])
        for identifier in ("118305", "118958", "119259", "119261", "119662", "119675", "119682", "119779", "119834"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for literal in ("语云", "語云", "語雲"):
            self.assertEqual(to_traditional(literal), "語云")
            self.assertEqual(to_traditional(to_traditional(literal)), "語云")
        for literal in ("白雲", "雲端語音", "語雲以外"):
            self.assertEqual(to_traditional(literal), literal)

    def test_sixty_third_batch_checks_financial_senses_and_prior_weight_repair(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_63}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_63}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 63), meta["input_curated_sha256"])
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["unreviewed_pool_candidates"], 24608)
        self.assertEqual(meta["reading_repairs"], 1)
        batch = [r for r in curated if r.get("batch") == BATCH_63]
        self.assertEqual(len(batch), 1086)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("貴行", "gwai3 hong4"), ("賈禍", "gu2 wo6"), ("賈禍", "gwu2 wo6"),
                            ("賺大錢", "zaan6 daai6 cin2"), ("負擔重", "fu6 daam1 cung5"),
                            ("貧鈾彈", "pan4 jau4 daan6"), ("貨幣匯率", "fo3 bai6 wui6 leot6"),
                            ("貿易商行", "mau6 jik6 soeng1 hong4"), ("賢相", "jin4 soeng3"),
                            ("足數", "zuk1 sou3"), ("贏到", "jeng4 dou2"), ("贏到", "jeng4 dou3"),
                            ("貯水池", "cyu5 seoi2 ci4"), ("貯水池", "cyu2 seoi2 ci4"),
                            ("豪華轎車", "hou4 waa4 giu2 ce1"), ("豪華轎車", "hou4 waa4 kiu2 ce1"),
                            ("購貨券", "kau3 fo3 hyun3"), ("購貨券", "kau3 fo3 gyun3"),
                            ("走到", "zau2 dou3"), ("負負得正", "fu6 fu6 dak1 zing3")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("貴行", "gwai3 haang4"), ("賈禍", "gaa2 wo6"),
                            ("賺大錢", "zaan6 daai6 cin4"), ("負擔重", "fu6 daam1 cung4"),
                            ("貨幣匯率", "fo3 bai6 wui6 leot2"),
                            ("足數", "zuk1 sou2"), ("賢相", "jin4 soeng1")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["120281"]["verdict"], "reject")
        self.assertEqual(by_id["121808"]["verdict"], "reject")
        for identifier in ("120281", "120282", "121391", "121485", "121539", "121808", "121827", "121848"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        repair = by_id["118502"]
        self.assertEqual((repair["verdict"], repair["previous_jyutping"], repair["jyutping"]),
                         ("repair", "jyu5 cung4 cing4 sam1", "jyu5 zung6 cing4 sam1"))
        current = {(r["char"], r["jyutping"]) for r in curated}
        self.assertIn(("語重情深", "jyu5 zung6 cing4 sam1"), current)
        self.assertNotIn(("語重情深", "jyu5 cung4 cing4 sam1"), current)
        for literal in ("艳后", "豔后", "豔後"):
            self.assertEqual(to_traditional(literal), "豔后")
            self.assertEqual(to_traditional(to_traditional(literal)), "豔后")
        for literal in ("皇后", "最後", "以後", "豔後以外"):
            self.assertEqual(to_traditional(literal), literal)

    def test_sixty_fourth_batch_checks_motion_transfer_and_generated_source_readings(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_64}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_64}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 64), meta["input_curated_sha256"])
        self.assertEqual(meta["input_curated_rows"], 73386)
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["unreviewed_pool_candidates"], 22608)
        self.assertEqual(meta["reading_repairs"], 0)
        batch = [r for r in curated if r.get("batch") == BATCH_64]
        self.assertEqual(len(batch), 1123)
        self.assertEqual(len({r["char"] for r in batch}), 979)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("身中數彈", "san1 zung3 sou3 daan6"), ("身中數槍", "san1 zung3 sou3 coeng1"),
                            ("踩油門", "caai2 jau4 mun4"), ("跨行", "kwaa1 hong4"), ("跨行", "kwaa3 hong4"),
                            ("軋鋼機", "zaat3 gong3 gei1"), ("轉喻", "zyun3 jyu6"),
                            ("轉圜之地", "zyun2 waan4 zi1 dei6"), ("轉圜之地", "zyun3 waan4 zi1 dei6"),
                            ("轉換成", "zyun2 wun6 sing4"), ("轉換成", "zyun3 wun6 sing4"),
                            ("踢棉被", "tek3 min4 pei5"), ("踢棉被", "tek3 min4 bei2"),
                            ("辣椒乾", "laat6 ziu1 gon1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("身中數彈", "san1 zung1 sou2 daan2"), ("踩油門", "caai2 jau2 mun4"),
                            ("跨行", "kwaa1 haang4"), ("轉喻", "zyun2 jyu6")]:
            self.assertNotIn((literal, jp), pairs)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["123311"]["verdict"], "reject")  # Within 輕輕鬆鬆.
        for identifier in ("122117", "122157", "122223", "122358", "122689", "123183", "123311", "123623", "123665"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        repairs = meta["existing_source_reading_repairs"]["repairs"]
        self.assertEqual({(r["char"], r["old_jyutping"], r["new_jyutping"], r["source"], r["source_flags"]) for r in repairs},
                         {("跟上", "gan1 soeng6", "gan1 soeng5", "hsk30", 1), ("踏上", "daap6 soeng6", "daap6 soeng5", "hsk30", 1)})
        for repair in repairs:
            raw = ROOT / repair["raw_path"]
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), repair["raw_sha256"])
            self.assertEqual(raw.read_text(encoding="utf-8-sig").splitlines()[repair["raw_line"] - 1].split()[-1], repair["raw_literal"])
            self.assertFalse(repair["raw_contains_jyutping"])
        original = [LexiconCandidate(r["char"], r["old_jyutping"], r["old_code"], ("hsk30",)) for r in repairs]
        unaffected = LexiconCandidate("上升", "soeng6 sing1", get_0243_code("soeng6 sing1"), ("fixture",))
        fixed = apply_lexicon_overlay([*original, unaffected], load_corrections())
        self.assertEqual([(r.char, r.jyutping, r.code, r.sources) for r in fixed],
                         [("跟上", "gan1 soeng5", "35", ("hsk30",)), ("踏上", "daap6 soeng5", "25", ("hsk30",)),
                          (unaffected.char, unaffected.jyutping, unaffected.code, unaffected.sources)])
        for literal in ("辣椒干", "辣椒幹", "辣椒乾"):
            self.assertEqual(to_traditional(literal), "辣椒乾")
            self.assertEqual(to_traditional(to_traditional(literal)), "辣椒乾")
        for literal in ("乾旱", "幹部", "辣椒幹以外"):
            self.assertEqual(to_traditional(literal), literal)

    def test_sixty_fifth_batch_preserves_nominal_tones_and_word_boundaries(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_65}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_65}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 65), meta["input_curated_sha256"])
        self.assertEqual(meta["input_curated_rows"], 74509)
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 7)
        self.assertEqual(meta["unreviewed_pool_candidates"], 20608)
        self.assertEqual(meta["reading_repairs"], 5)
        batch = [r for r in curated if r.get("batch") == BATCH_65]
        self.assertEqual(len(batch), 1164)
        self.assertEqual(len({r["char"] for r in batch}), 972)  # Includes two old forms gaining a reading.
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("近程導彈", "gan6 cing4 dou6 daan2"), ("近程導彈", "gan6 cing4 dou6 daan6"),
                            ("迫擊炮彈", "bik1 gik1 paau3 daan2"), ("迫擊炮彈", "bik1 gik1 paau3 daan6"),
                            ("通緝逃犯", "tung1 cap1 tou4 faan2"), ("通緝逃犯", "tung1 cap1 tou4 faan6"),
                            ("貧鈾彈", "pan4 jau4 daan2"), ("身中數彈", "san1 zung3 sou3 daan2"),
                            ("追到手", "zeoi1 dou2 sau2"), ("這行", "ze5 hong4"), ("這行", "ze2 hong4"), ("這行", "ze3 hong4"),
                            ("這番話", "ze5 faan1 waa6"), ("迴腸寸斷", "wui4 coeng4 cyun3 dyun6"),
                            ("迴腸百轉", "wui4 coeng4 baak3 zyun2"), ("連皮帶肉", "lin4 pei4 daai3 juk6"),
                            ("運算量", "wan6 syun3 loeng6"), ("通話量", "tung1 waa6 loeng6"),
                            ("游向", "jau4 hoeng3"), ("游進", "jau4 zeon3"), ("游開", "jau4 hoi1"),
                            ("回歸係數", "wui4 gwai1 hai6 sou3"), ("逸興", "jat6 hing3"),
                            ("逾重", "jyu4 cung5"), ("逾重", "jyu6 zung6"), ("運轉不暢", "wan6 zyun2 bat1 coeng3"),
                            ("連帶處分", "lin4 daai3 cyu2 fan1"), ("連帶處分", "lin4 daai3 cyu5 fan1")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("追到手", "zeoi1 dou3 sau2"), ("這行", "ze5 haang4"),
                            ("迴腸寸斷", "wui4 coeng2 cyun3 dyun6"), ("連皮帶肉", "lin4 pei4 daai2 juk6"),
                            ("逸興", "jat6 hing1"), ("逾重", "jyu6 cung4")]:
            self.assertNotIn((literal, jp), pairs)
        for kuang in ("kwaang3", "gwaang6", "gwaang3"):
            for meeting in ("wui2", "wui6"):
                self.assertIn(("逛廟會", f"{kuang} miu2 {meeting}"), pairs)
        allpairs = {(r["char"], r["jyutping"]) for r in curated}
        for literal, jp in [("貧鈾彈", "pan4 jau4 daan6"), ("身中數彈", "san1 zung3 sou3 daan6")]:
            self.assertIn((literal, jp), allpairs)  # Existing book readings remain valid.
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["貧鈾彈", "pan4 jau4 daan2"], "預設")
        self.assertEqual(ranks["貧鈾彈", "pan4 jau4 daan6"], "常用")
        self.assertEqual(ranks["身中數彈", "san1 zung3 sou3 daan6"], "預設")
        self.assertEqual(ranks["身中數彈", "san1 zung3 sou3 daan2"], "常用")
        repairs = [r for r in review if r["verdict"] == "repair"]
        self.assertEqual({r["char"] for r in repairs}, {"行政處分", "停刊處分", "停工處分", "停業處分", "刑事處分"})
        for repair in repairs:
            self.assertTrue(repair["previous_jyutping"].endswith("fan6"))
            self.assertTrue(repair["jyutping"].endswith("fan1"))
            self.assertIn((repair["char"], repair["jyutping"]), allpairs)
            self.assertNotIn((repair["char"], repair["previous_jyutping"]), allpairs)
        existing = meta["existing_source_reading_repairs"]
        self.assertEqual(existing["old_runtime_readings_deleted"], 0)
        self.assertEqual(existing["old_overlay_rows_added"], 0)
        self.assertEqual(len(existing["prior_reading_additions"]), 2)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["124478"]["verdict"], "reject")  # Within 以退為進.
        for identifier in ("124340", "124405", "124478", "124595", "124597", "124626", "124796", "124822", "124823", "124841", "124845", "124855", "124859", "124860", "125460", "125647", "125657", "125864"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for target, variants in [("回歸係數", ("回归系数", "迴歸係數", "回歸係數")),
                                 ("回歸方程", ("回归方程", "迴歸方程", "回歸方程")),
                                 ("回歸祖國", ("回归祖国", "迴歸祖國", "回歸祖國")),
                                 ("逐步回歸", ("逐步回归", "逐步迴歸", "逐步回歸")),
                                 ("游向", ("游向",)), ("游進", ("游进", "游進")), ("游開", ("游开", "游開"))]:
            for literal in variants:
                self.assertEqual(to_traditional(literal), target)
                self.assertEqual(to_traditional(to_traditional(literal)), target)
        for literal in ("遊向", "遊進", "遊開", "遊覽", "迴旋", "迴歸係數以外"):
            self.assertEqual(to_traditional(literal), literal)

    def test_sixty_sixth_batch_preserves_word_senses_and_attested_changed_tones(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_66}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_66}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 66), meta["input_curated_sha256"])
        self.assertEqual(meta["input_curated_rows"], 75673)
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 2)
        self.assertEqual(meta["reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 18608)
        batch = [r for r in curated if r.get("batch") == BATCH_66]
        self.assertEqual(len(batch), 1095)
        self.assertEqual(len({r["char"] for r in batch}), 1020)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("道義上", "dou6 ji6 soeng6"), ("遙相應和", "jiu4 soeng1 jing3 wo6"),
                            ("遣兵調將", "hin2 bing1 diu6 zoeng3"), ("遣將調兵", "hin2 zoeng3 diu6 bing1"),
                            ("違紀處分", "wai4 gei2 cyu2 fan1"), ("違紀處分", "wai4 gei3 cyu5 fan1"),
                            ("那行", "naa5 hong4"), ("那怎麼行", "naa5 zam2 mo1 haang4"),
                            ("郡長", "gwan6 zoeng2"), ("部會首長", "bou6 wui6 sau2 zoeng2"),
                            ("郵政局長", "jau4 zing3 guk6 zoeng2"), ("鄰長", "leon4 zoeng2"),
                            ("醫治創傷", "ji1 zi6 cong1 soeng1"), ("避難趨易", "bei6 naan4 ceoi1 ji6"),
                            ("重估價", "cung4 gu2 gaa3"), ("重估", "cung4 gu2"),
                            ("重低音", "cung5 dai1 jam1"), ("重低音", "zung6 dai1 jam1"),
                            ("重情", "zung6 cing4"), ("重情義", "zung6 cing4 ji6"),
                            ("重彈老調", "cung4 taan4 lou5 diu6"),
                            ("酗酒滋事", "jyu3 zau2 zi1 si6"), ("酗酒滋事", "jyu1 zau2 zi1 si6"),
                            ("酗酒滋事", "heoi3 zau2 zi1 si6"), ("酗酒", "heoi3 zau2"), ("酗酒", "jyu1 zau2"),
                            ("醃成", "jip3 sing4"), ("醃成", "jim1 sing4"),
                            ("酒店傢俱", "zau2 dim3 gaa1 geoi6"), ("酒店傢俱", "zau2 dim3 gaa1 keoi1"),
                            ("郵費付訖", "jau4 fai3 fu6 gat1"), ("郵費付訖", "jau4 fai3 fu6 ngat6"),
                            ("酒吧女", "zau2 baa1 neoi2"), ("酒吧女", "zau2 baa1 neoi5"),
                            ("遠征隊", "jyun5 zing1 deoi6"), ("鄰里關係", "leon4 lei5 gwaan1 hai6")]:
            self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("道義上", "dou6 ji6 soeng5"), ("遙相應和", "jiu4 soeng1 jing3 wo4"),
                            ("那行", "naa5 haang4"), ("郡長", "gwan6 coeng4"),
                            ("重低音", "cung4 dai1 jam1"), ("重情", "cung4 cing4"),
                            ("重彈老調", "cung4 daan2 lou5 diu6"), ("醫治創傷", "ji1 zi6 cong3 soeng1")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for literal, jp in [("郵費付訖", "jau4 fai3 fu6 gat1"), ("酒吧女", "zau2 baa1 neoi2"), ("酒吧街", "zau2 baa1 gaai1"), ("重估", "cung4 gu2")]:
            self.assertEqual(ranks[literal, jp], "預設")
        self.assertEqual(ranks["酗酒", "jyu1 zau2"], "常用")
        self.assertEqual(ranks["酗酒", "heoi3 zau2"], "常用")
        self.assertEqual(meta["existing_runtime_readings_mirrored"], 1)
        self.assertEqual(meta["existing_word_new_readings"], 2)
        self.assertEqual(meta["existing_source_reading_repairs"]["old_runtime_readings_deleted"], 0)
        by_id = {r["id"]: r for r in review}
        self.assertEqual(by_id["127035"]["verdict"], "reject")  # 還／著緊 boundary.
        for identifier in ("126005", "126414", "126606", "126678", "127032", "127035", "127179", "127982"):
            self.assertIn("Cantopop-corpus/blob/018e885", by_id[identifier]["reading_reference"])
        for target, variants in [("遠征隊", ("远征队", "遠徵隊", "遠征隊")),
                                 ("鄉里鄉親", ("乡里乡亲", "鄉裏鄉親", "鄉里鄉親")),
                                 ("鄰里公園", ("邻里公园", "鄰裏公園", "鄰里公園")),
                                 ("鄰里糾紛", ("邻里纠纷", "鄰裏糾紛", "鄰里糾紛")),
                                 ("鄰里關係", ("邻里关系", "鄰裏關係", "鄰里關係"))]:
            for literal in variants:
                self.assertEqual(to_traditional(literal), target)
                self.assertEqual(to_traditional(to_traditional(literal)), target)
        for literal in ("鄰裏", "街坊鄰裏", "裏面", "公里", "鄰裏關係以外", "遠徵隊以外"):
            self.assertEqual(to_traditional(literal), literal)
        migrations = meta["normalization_impact"]["explicit_runtime_literal_migrations"]
        self.assertEqual(migrations, [{"previous_char": "鄉裏鄉親", "char": "鄉里鄉親", "jyutping": "hoeng1 lei5 hoeng1 can1", "code": "3533", "source_flags": 16}])

    def test_sixty_seventh_batch_preserves_valid_variants_and_filters_exact_errors(self):
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        path = REVIEW.parent / f"{BATCH_67}-supplement.tsv"
        meta = json.loads((REVIEW.parent / f"{BATCH_67}.meta.json").read_text(encoding="utf-8"))
        review = review_rows(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual(input_fingerprint(curated, meta, 67), meta["input_curated_sha256"])
        self.assertEqual(meta["input_curated_rows"], 76768)
        self.assertEqual(meta["newly_reviewed_candidates"], 2000)
        self.assertEqual(meta["revisited_candidates"], 5)
        self.assertEqual(meta["reading_repairs"], 2)
        self.assertEqual(meta["curated_source_reading_repairs"], 0)
        self.assertEqual(meta["unreviewed_pool_candidates"], 16608)
        batch = [r for r in curated if r.get("batch") == BATCH_67]
        self.assertEqual(len(batch), 1016)
        self.assertEqual(len({r["char"] for r in batch}), 847)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review if r["verdict"] == "accept"},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in batch})
        pairs = {(to_traditional(r["char"]), r["jyutping"]) for r in batch}
        for literal, jp in [("重新加油", "cung4 san1 gaa1 jau2"), ("重新加油", "cung4 san1 gaa1 jau4"),
                            ("重新部署", "cung4 san1 bou6 cyu5"), ("銀邊眼鏡", "ngan4 bin1 ngaan5 geng2"),
                            ("鏈接庫", "lin4 zip3 fu3"), ("重畫", "cung4 waa6"), ("重義氣", "zung6 ji6 hei3"),
                            ("量子數", "loeng6 zi2 sou3"), ("金牌數", "gam1 paai4 sou3"),
                            ("釘釘子", "deng1 deng1 zi2"), ("釘釘子", "ding1 ding1 zi2"), ("釘釘子", "ding3 ding1 zi2"),
                            ("重點", "zung6 dim2"), ("重點", "cung5 dim2"), ("鑽孔", "zyun1 hung2"),
                            ("訂書釘", "deng1 syu1 deng1"), ("錦綸絲", "gam2 leon4 si1"),
                            ("錯上加錯", "co3 soeng6 gaa1 co3"), ("鐵槓", "tit3 gong3"), ("鐵路局長", "tit3 lou6 guk6 zoeng2")]:
            self.assertIn((literal, jp), pairs)
        for literal, jp in [("重新部署", "cung4 san1 bou6 cyu2"), ("重畫", "cung4 waa2"),
                            ("重義氣", "cung4 ji6 hei3"), ("量子數", "loeng6 zi2 sou2"),
                            ("金牌數", "gam1 paai4 sou2"), ("鐵槓", "tit3 gung3"), ("鐵路局長", "tit3 lou6 guk6 coeng4")]:
            self.assertNotIn((literal, jp), pairs)
        ranks = {(r["char"], r["jyutping"]): r["pron_rank"] for r in json.loads(CURATED.with_name("curated_reading_ranks.json").read_text(encoding="utf-8"))}
        for literal, jp in [("重新加油", "cung4 san1 gaa1 jau2"), ("銀邊眼鏡", "ngan4 bin1 ngaan5 geng2"),
                            ("鏈接庫", "lin4 zip3 fu3"), ("重點", "zung6 dim2"), ("鑽孔", "zyun1 hung2"), ("訂書釘", "deng1 syu1 deng1")]:
            self.assertEqual(ranks[literal, jp], "預設")
        self.assertEqual(ranks["重點", "cung5 dim2"], "常用")
        # Modern verb ding3 remains valid; the correction concerns 仲 alone.
        old = LexiconCandidate("鐵板釘釘", "tit3 baan2 ding3 ding1", get_0243_code("tit3 baan2 ding3 ding1"), ("fixture",))
        fixture = [old]
        for literal, wrong, correct in [("爛船仲有三斤釘", "laan6 syun4 zung3 jau5 saam1 gan1 deng1", "laan6 syun4 zung6 jau5 saam1 gan1 deng1"),
                                         ("爛船都仲有三斤釘", "laan6 syun4 dou1 zung3 jau5 saam1 gan1 deng1", "laan6 syun4 dou1 zung6 jau5 saam1 gan1 deng1")]:
            fixture.extend(LexiconCandidate(literal, jp, get_0243_code(jp), ("fixture",)) for jp in (wrong, correct))
        fixed = apply_lexicon_overlay(fixture, load_corrections())
        self.assertIn(old, fixed)
        self.assertEqual(len(fixed), 3)
        self.assertTrue(all("zung3" not in r.jyutping for r in fixed))
        self.assertEqual(meta["existing_runtime_readings_mirrored"], 2)
        self.assertEqual(meta["existing_word_new_readings"], 2)
        self.assertEqual(meta["normalization_impact"]["explicit_runtime_literal_migrations"], [])
        for target, variants in [("舖頭", ("铺头", "鋪頭", "舖頭")), ("鍾意", ("钟意", "鐘意", "鍾意")), ("鐘狀", ("钟状", "鍾狀", "鐘狀"))]:
            for literal in variants:
                self.assertEqual(to_traditional(literal), target)
                self.assertEqual(to_traditional(to_traditional(literal)), target)
        for literal in ("鋪路", "鋪地板", "鐘聲", "鍾情", "鍾愛", "鍾狀期", "鐘意以外", "鋪頭以外"):
            self.assertEqual(to_traditional(literal), literal)

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
