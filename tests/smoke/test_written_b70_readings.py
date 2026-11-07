"""B70 keeps whole-word senses and stays inside the frozen candidate scope."""
import csv
import hashlib
import io
import json
from pathlib import Path
import unittest

from app.utils.trad_chinese import to_traditional
from ingest.lexicon_sources import ingest_lexicon_json

ROOT = Path(__file__).resolve().parents[2]
BATCH = "2026-11-06-written-b70"


class WrittenB70ReadingsTests(unittest.TestCase):
    def test_context_readings_and_modern_variants_survive_ingest(self):
        pairs = {(r.char, r.jyutping) for r in ingest_lexicon_json(
            ROOT / "data/lexicon/curated_lexicon.json", source_id="curated")}
        for literal, readings in {
            "音樂作品": ["jam1 ngok6 zok3 ban2"],
            "頂呱呱": ["ding2 gwaa1 gwaa1"],
            "顯著性": ["hin2 zyu3 sing3"],
            "面部輪廓": ["min6 bou6 leon4 kwok3"],
            "預先付訖": ["jyu6 sin1 fu6 ngat6", "jyu6 sin1 fu6 gat1"],
            "顛倒乾坤": ["din1 dou2 kin4 kwan1"],
            "預備會議": ["jyu6 bei6 wui6 ji5"],
            "領隊證": ["ling5 deoi2 zing3"],
            "飄泊不定": ["piu1 bok6 bat1 ding6"],
            "順勢上漲": ["seon6 sai3 soeng6 zoeng3", "seon6 sai3 soeng5 zoeng3", "seon6 sai3 soeng6 zoeng2"],
            "顯示桌面": ["hin2 si6 coek3 min2", "hin2 si6 zoek3 min2", "hin2 si6 coek3 min6", "hin2 si6 zoek3 min6"],
            "音樂視聽": ["jam1 ngok6 si6 ting3", "jam1 ngok6 si6 ting1", "jam1 ngok6 si6 teng1"],
            "預料之中": ["jyu6 liu2 zi1 zung1", "jyu6 liu6 zi1 zung1"],
        }.items():
            for jp in readings:
                with self.subTest(literal=literal, jyutping=jp):
                    self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("音樂作品", "jam1 lok6 zok3 ban2"),
                            ("頂呱呱", "ding2 gwek4 gwek2"),
                            ("顯著性", "hin2 zoek3 sing3"),
                            ("顛倒乾坤", "din1 dou2 gon1 kwan1")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)

    def test_review_preserves_prior_source_and_rejects_boundary_fragments(self):
        base = ROOT / "data/lexicon"
        meta = json.loads((base / f"reviews/{BATCH}.meta.json").read_text(encoding="utf-8"))
        review_path = base / f"reviews/{BATCH}-supplement.tsv"
        review = list(csv.DictReader(io.StringIO(review_path.read_text(encoding="utf-8")), delimiter="\t"))
        self.assertEqual(hashlib.sha256(review_path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        ids = {int(r["id"].split(":")[0]) for r in review}
        self.assertEqual(ids, set(range(133994, 135994)))
        self.assertTrue(meta["fixed_final_scope"]["candidate_discovery_closed"])
        self.assertEqual(meta["fixed_final_scope"]["last_remaining_id"], 146601)
        source = json.loads((base / "curated_lexicon.json").read_text(encoding="utf-8"))
        prefix = json.dumps(source[:meta["input_curated_rows"]], ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(), meta["input_curated_sha256"])
        added = {r["char"] for r in source if r.get("batch") == BATCH}
        self.assertTrue(added.isdisjoint({"面有", "頭額", "風不", "面貼膜", "頗見好評", "靠邊兒站", "順杆兒爬", "頭殼壞去"}))
        for literal in ["面有", "頭額", "風不"]:
            self.assertTrue(any(r["char"] == literal and r["verdict"] == "reject" for r in review))


if __name__ == "__main__":
    unittest.main()
