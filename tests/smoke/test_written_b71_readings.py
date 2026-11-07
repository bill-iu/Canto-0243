"""Whole-word tone changes, ranked modern variants and one exact source exclusion."""
import csv
import hashlib
import io
import json
from pathlib import Path
import unittest

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import load_corrections
from app.utils.jyutping_codec import get_0243_code
from app.utils.trad_chinese import to_traditional
from ingest.lexicon_overlay import apply_lexicon_overlay
from ingest.lexicon_sources import ingest_lexicon_json

ROOT = Path(__file__).resolve().parents[2]
BATCH = "2026-11-06-written-b71"


class WrittenB71ReadingsTests(unittest.TestCase):
    def test_compound_tones_and_modern_variants_survive_ingest(self):
        path = ROOT / "data/lexicon/curated_lexicon.json"
        pairs = {(r.char, r.jyutping) for r in ingest_lexicon_json(path, source_id="curated")}
        expected = {
            "餐桌上": ["caan1 coek3 soeng6", "caan1 zoek3 soeng6"],
            "馬路上": ["maa5 lou6 soeng6"],
            "首映會": ["sau2 jing2 wui2", "sau2 jing2 wui6"],
            "餅餡": ["beng2 haam2", "beng2 haam6"],
            "餘音繚繞": ["jyu4 jam1 liu4 jiu2", "jyu4 jam1 liu4 jiu5"],
            "魚皮": ["jyu4 pei4"],
            "魚膠粉": ["jyu4 gaau1 fan2"],
            "魚頭湯": ["jyu4 tau4 tong1"],
            "魷魚乾": ["jau4 jyu4 gon1"],
            "魷魚絲": ["jau4 jyu4 si1"],
            "鯽魚湯": ["zak1 jyu4 tong1", "zik1 jyu4 tong1"],
            "騎驢找馬": ["ke4 lou4 zaau2 maa5", "ke4 leoi4 zaau2 maa5"],
            "鴉片煙癮": ["aa1 pin3 jin1 jan5", "aa1 pin3 jin1 jan2"],
            "高黏度": ["gou1 nim1 dou6", "gou1 nim4 dou6"],
            "高熱量": ["gou1 jit6 loeng6"],
            "高中生物": ["gou1 zung1 sang1 mat6"],
            "高速旋轉": ["gou1 cuk1 syun4 zyun2"],
            "發卡行": ["faat3 kaat1 hong4", "faat3 kaa1 hong4"],
            "驚悚片": ["ging1 sung2 pin2", "ging1 sung2 pin3"],
        }
        for word, readings in expected.items():
            for jp in readings:
                with self.subTest(word=word, jyutping=jp):
                    self.assertIn((to_traditional(word), jp), pairs)
        source = json.loads(path.read_text(encoding="utf-8"))
        new_pairs = {(to_traditional(r["char"]), r["jyutping"])
                     for r in source if r.get("batch") == BATCH}
        for word, jp in [("餐桌上", "caan1 coek3 soeng5"),
                         ("魚皮", "jyu2 pei4"),
                         ("魷魚乾", "jau4 jyu2 gon1"),
                         ("高中生物", "gou1 zung1 saang1 mat6"),
                         ("發卡行", "faat3 kaa1 haang4")]:
            self.assertNotIn((to_traditional(word), jp), new_pairs)

    def test_review_stays_in_fixed_pool_and_preserves_source_prefix(self):
        base = ROOT / "data/lexicon"
        meta = json.loads((base / f"reviews/{BATCH}.meta.json").read_text(encoding="utf-8"))
        review_path = base / f"reviews/{BATCH}-supplement.tsv"
        review = list(csv.DictReader(io.StringIO(review_path.read_text(encoding="utf-8")), delimiter="\t"))
        self.assertEqual(hashlib.sha256(review_path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        self.assertEqual({int(r["id"].split(":")[0]) for r in review}, set(range(135994, 137994)))
        self.assertTrue(meta["fixed_final_scope"]["candidate_discovery_closed"])
        self.assertEqual(meta["candidate_pool"], 146602)
        source = json.loads((base / "curated_lexicon.json").read_text(encoding="utf-8"))
        prefix = json.dumps(source[:meta["input_curated_rows"]], ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(), meta["input_curated_sha256"])
        added = {r["char"] for r in source if r.get("batch") == BATCH}
        self.assertTrue(added.isdisjoint({"驚魂落魄", "騰讓", "魔塔", "高瞻遠囑", "鬼鬼崇崇", "騙腿", "鬼丫頭", "魂鬥羅"}))

    def test_exact_ghost_work_exclusion_preserves_special_san1(self):
        corrections = [r for r in load_corrections() if r.note.startswith("B71 整詞覆核：")]
        self.assertEqual(len(corrections), 1)
        bad = LexiconCandidate("鬼斧神工", "gwai2 fu2 san1 gung1", "9933", ("rime_cantonese",))
        good = LexiconCandidate("鬼斧神工", "gwai2 fu2 san4 gung1", "9903", ("words_hk",))
        special = LexiconCandidate("神荼", "san1 syu1", get_0243_code("san1 syu1"), ("rime_cantonese",))
        bare = LexiconCandidate("神", "san1", "3", ("rime_char",))
        self.assertEqual(apply_lexicon_overlay([bad, good, special, bare], corrections), [good, special, bare])


if __name__ == "__main__":
    unittest.main()
