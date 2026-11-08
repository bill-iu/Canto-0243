"""B69 whole-word readings survive admission, correction and display ranking."""
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


class WrittenB69ReadingsTests(unittest.TestCase):
    def test_whole_word_readings_and_valid_variants_survive_ingest(self):
        pairs = {(r.char, r.jyutping) for r in ingest_lexicon_json(
            ROOT / "data/lexicon/curated_lexicon.json", source_id="curated")}
        for literal, readings in {
            "雞翅膀": ["gai1 ci3 pong4"],
            "集中力量": ["zaap6 zung1 lik6 loeng6"],
            "集會自由": ["zaap6 wui2 zi6 jau4", "zaap6 wui6 zi6 jau4"],
            "難以相處": ["naan4 ji5 soeng1 cyu5", "naan4 ji5 soeng1 cyu3", "naan4 ji5 soeng1 cyu2"],
            "非承重牆": ["fei1 sing4 cung5 coeng4"],
            "電錶箱": ["din6 biu1 soeng1"],
            "零冠詞": ["ling4 gun3 ci4"],
            "非分之財": ["fei1 fan6 zi1 coi4"],
            "與人相處": ["jyu5 jan4 soeng1 cyu5"],
        }.items():
            for jp in readings:
                with self.subTest(literal=literal, jyutping=jp):
                    self.assertIn((to_traditional(literal), jp), pairs)
        for literal, jp in [("雙位數", "soeng1 wai6 sou2"), ("零冠詞", "ling4 gun1 ci4"),
                            ("電錶箱", "din6 biu2 soeng1"), ("電子干擾", "din6 zi2 gon3 jiu2")]:
            self.assertNotIn((to_traditional(literal), jp), pairs)

    def test_exact_relative_pronunciation_repair_preserves_valid_cyu3(self):
        original = LexiconCandidate("與人相處", "jyu5 jan4 soeng3 cyu2",
                                    get_0243_code("jyu5 jan4 soeng3 cyu2"), ("rime_words",))
        valid = LexiconCandidate("相處", "soeng1 cyu3", get_0243_code("soeng1 cyu3"), ("words_hk",))
        result = apply_lexicon_overlay([original, valid], load_corrections())
        pairs = {(r.char, r.jyutping) for r in result}
        self.assertEqual(pairs, {("與人相處", "jyu5 jan4 soeng1 cyu2"), ("相處", "soeng1 cyu3")})
        self.assertTrue(all(r.code == get_0243_code(r.jyutping) for r in result))
        self.assertEqual(next(r for r in result if r.char == "與人相處").sources, original.sources)

    def test_reading_preference_is_separate_from_word_familiarity(self):
        labels = ["預設", "常用", "罕見", "棄用"]
        ranks = {(r["char"], r["jyutping"]): labels.index(r["pron_rank"])
                 for r in json.loads((ROOT / "data/lexicon/curated_reading_ranks.json").read_text(encoding="utf-8"))}
        self.assertEqual(ranks["與人相處", "jyu5 jan4 soeng1 cyu5"], 0)
        self.assertLess(ranks["難以相處", "naan4 ji5 soeng1 cyu5"], ranks["難以相處", "naan4 ji5 soeng1 cyu3"])
        self.assertLess(ranks["集會自由", "zaap6 wui2 zi6 jau4"], ranks["集會自由", "zaap6 wui6 zi6 jau4"])


if __name__ == "__main__":
    unittest.main()
