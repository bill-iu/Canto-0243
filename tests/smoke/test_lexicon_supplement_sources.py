"""Supplement lexicon source parsers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_build import DEFAULT_LEXICON_MANIFEST
from ingest.lexicon_merge import merge_lexicon_candidates
from ingest.lexicon_sources import (
    empty_rime_phrase_stats,
    ingest_hsk30_wordlist,
    ingest_lexicon_json,
    ingest_rime_phrase_yaml,
    ingest_rime_upstream_csvs,
    ingest_rime_words_yaml,
    ingest_words_hk_wordslist,
    resolve_generated_jyutping,
)
from ingest.lexicon_candidate_normalizer import (
    DefaultLexiconCandidateStrategy,
    LexiconCandidateNormalizer,
)
from ingest.lexicon_validate import build_mixed_literal_code, is_valid_word_lexicon_reading
from ingest.syn_ant_manifest import load_manifest


SUPPLEMENT_RAW_PARSERS = {
    "hsk30_wordlist",
    "kaifang_txt",
    "rime_phrase_yaml",
    "rime_upstream_csv",
    "rime_words_yaml",
    "words_hk_wordslist",
}


class LexiconSupplementSourceTests(unittest.TestCase):
    def test_rime_upstream_csvs_keep_words_and_exclude_proper_nouns(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "word.csv").write_text(
                "char,jyutping\n三字詞,saam1 zi6 ci4\n四字成語,sei3 zi6 sing4 jyu5\n"
                "某某公司,mau5 mau5 gung1 si1\n某某銀行,mau5 mau5 ngan4 hong4\n"
                "某某中心,mau5 mau5 zung1 sam1\n某某委員會,mau5 mau5 wai2 jyun4 wui2\n",
                encoding="utf-8",
            )
            (root / "fixed_expressions.csv").write_text(
                "char,jyutping\n畫蛇添足,waak6 se4 tim1 zuk1\n",
                encoding="utf-8",
            )
            (root / "proper_nouns.csv").write_text(
                "category,char,jyutping\n機構,某某公司,mau5 mau5 gung1 si1\n"
                "機構,某某銀行,mau5 mau5 ngan4 hong4\n"
                "機構,某某中心,mau5 mau5 zung1 sam1\n",
                encoding="utf-8",
            )

            rows = ingest_rime_upstream_csvs(root / "word.csv", source_id="rime_words")

        self.assertEqual(
            {row.char for row in rows},
            {"三字詞", "四字成語", "畫蛇添足"},
        )
        self.assertTrue(all(row.sources == ("rime_words",) for row in rows))

    def test_hsk30_wordlist_converts_traditional_and_uses_pycantonese(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "wordlist.txt"
            path.write_text("后台\n一级词汇表\n", encoding="utf-8")

            def fake_reading(text: str) -> str | None:
                # s2hk: 后台 → 後台 (HK 台, not TW 臺)
                return "hau6 toi4" if text == "後台" else None

            with patch("ingest.lexicon_sources._full_pycantonese_reading", side_effect=fake_reading):
                rows = ingest_hsk30_wordlist(path, source_id="hsk30")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].char, "後台")
        self.assertEqual(rows[0].jyutping, "hau6 toi4")
        self.assertEqual(rows[0].sources, ("hsk30",))

    def test_generated_jyutping_falls_back_to_pyjyutping(self):
        with patch("ingest.lexicon_sources._full_pycantonese_reading", return_value=None):
            with patch("ingest.lexicon_sources._full_pyjyutping_reading", return_value="ko1 zung1"):
                self.assertEqual(resolve_generated_jyutping("Call鐘"), "ko1 zung1")

    def test_rime_words_yaml_parser_reads_body_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "jyut6ping3.words.dict.yaml"
            path.write_text(
                "# Rime dictionary\n---\nname: jyut6ping3.words\n...\n\n香港\thoeng1 gong2\nbad\n香港\thoeng1 gong2\n",
                encoding="utf-8",
            )
            rows = ingest_rime_words_yaml(path, source_id="rime_words")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].char, "香港")
        self.assertEqual(rows[0].jyutping, "hoeng1 gong2")
        self.assertEqual(rows[0].sources, ("rime_words",))

    def test_rime_phrase_reject_suffixes_file_blocks_shop_names_keeps_idiom_words(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "jyut6ping3.phrase.dict.yaml"
            allowlist = Path(d) / "allowlist.txt"
            reject = Path(d) / "reject-suffixes.txt"
            path.write_text(
                "\n".join(
                    [
                        "---",
                        "...",
                        "德馨茗茶",
                        "套路",
                        "高速公路",
                        "出路",
                    ]
                ),
                encoding="utf-8",
            )
            reject.write_text("茗茶\n建材\n", encoding="utf-8")
            readings = {
                "德馨茗茶": "dak1 hing1 ming4 caa4",
                "套路": "tou3 lou6",
                "高速公路": "gou1 suk6 gung1 lou6",
                "出路": "ceot1 lou6",
            }
            stats = empty_rime_phrase_stats()
            with patch("ingest.lexicon_sources.resolve_generated_jyutping", side_effect=readings.get):
                rows = ingest_rime_phrase_yaml(
                    path,
                    source_id="rime_phrase",
                    reject_suffixes_path=reject,
                    stats=stats,
                )
        by_char = {row.char: row for row in rows}
        self.assertEqual(set(by_char), {"套路", "出路"})
        self.assertEqual(stats["rejected_place_or_org"], 2)

    def test_rime_phrase_reject_literals_blocks_noise_keeps_true_words(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "jyut6ping3.phrase.dict.yaml"
            reject_lit = Path(d) / "reject-literals.txt"
            path.write_text(
                "\n".join(
                    [
                        "---",
                        "...",
                        "花園",
                        "金門",
                        "工程",
                        "出場",
                        "大門",
                    ]
                ),
                encoding="utf-8",
            )
            reject_lit.write_text("花園\n金門\n工程\n", encoding="utf-8")
            readings = {
                "花園": "faa1 jyun4",
                "金門": "gam1 mun4",
                "工程": "gung1 cing4",
                "出場": "ceot1 coeng4",
                "大門": "daai6 mun4",
            }
            stats = empty_rime_phrase_stats()
            with patch("ingest.lexicon_sources.resolve_generated_jyutping", side_effect=readings.get):
                rows = ingest_rime_phrase_yaml(
                    path,
                    source_id="rime_phrase",
                    reject_literals_path=reject_lit,
                    stats=stats,
                )
        by_char = {row.char: row for row in rows}
        self.assertEqual(set(by_char), {"出場", "大門"})
        self.assertEqual(stats["rejected_literal"], 3)

    def test_rime_phrase_parser_filters_noise_and_uses_8_char_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "jyut6ping3.phrase.dict.yaml"
            allowlist = Path(d) / "jyut6ping3.phrase.8char-allowlist.txt"
            path.write_text(
                "\n".join(
                    [
                        "# Rime phrase dictionary",
                        "---",
                        "name: jyut6ping3.phrase",
                        "...",
                        "書中自有黃金屋",
                        "不經一事不長一智",
                        "一二三四五六七八",
                        "一二三四五六七八九",
                        "香港中文大學",
                        "阿sir",
                    ]
                ),
                encoding="utf-8",
            )
            allowlist.write_text("不經一事不長一智\n", encoding="utf-8")
            readings = {
                "書中自有黃金屋": "syu1 zung1 zi6 jau5 wong4 gam1 uk1",
                "不經一事不長一智": "bat1 ging1 jat1 si6 bat1 zoeng2 jat1 zi3",
            }
            stats = empty_rime_phrase_stats()

            with patch("ingest.lexicon_sources.resolve_generated_jyutping", side_effect=readings.get):
                rows = ingest_rime_phrase_yaml(
                    path,
                    source_id="rime_phrase",
                    allowlist_path=allowlist,
                    stats=stats,
                )

        by_char = {row.char: row for row in rows}
        self.assertEqual(set(by_char), {"書中自有黃金屋", "不經一事不長一智"})
        self.assertEqual(by_char["不經一事不長一智"].sources, ("rime_phrase",))
        self.assertEqual(stats["accepted"], 2)
        self.assertEqual(stats["accepted_8_char_allowlisted"], 1)
        self.assertEqual(stats["rejected_8_char_needs_review"], 1)
        self.assertEqual(stats["rejected_long"], 1)
        self.assertEqual(stats["rejected_place_or_org"], 1)
        self.assertEqual(stats["rejected_mixed"], 1)

    def test_punctuation_in_phrase_is_ignored_for_reading_validation(self):
        self.assertTrue(
            is_valid_word_lexicon_reading(
                "犧牲小我，完成大我",
                "hei1 sang1 siu2 ngo5 jyun4 sing4 daai6 ngo5",
            )
        )

    def test_mixed_literal_words_hk_entries_use_pyjyutping_and_wildcard_code(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "wordslist.json"
            path.write_text('{"AV女優": ["ei1 wi1 neoi5 jau1"]}', encoding="utf-8")
            with patch("ingest.lexicon_validate._generate_mixed_literal_jyutping", return_value="ei1 wi1 neoi5 jau1"):
                rows = ingest_words_hk_wordslist(path, source_id="words_hk")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].char, "AV女優")
        self.assertEqual(rows[0].jyutping, "ei1 wi1 neoi5 jau1")
        self.assertEqual(rows[0].code, "??53")
        self.assertTrue(
            is_valid_word_lexicon_reading(
                "AV女優",
                "ei1 wi1 neoi5 jau1",
                allow_mixed_literal=True,
            )
        )
        self.assertEqual(build_mixed_literal_code("AV女優", "ei1 wi1 neoi5 jau1"), "??53")

    def test_generic_lexicon_json_uses_shared_mixed_literal_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "lexicon.json"
            path.write_text('[{"char": "AV女優", "jyutping": "ei1 wi1 neoi5 jau1", "code": ""}]', encoding="utf-8")
            rows = ingest_lexicon_json(path, source_id="lexicon_json")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].code, "??53")

    def test_candidate_normalizer_exposes_single_interface_for_mixed_literals(self):
        normalizer = LexiconCandidateNormalizer()
        candidate = normalizer.normalize_candidate("AV女優", "ei1 wi1 neoi5 jau1", source_id="words_hk")

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.char, "AV女優")
        self.assertEqual(candidate.code, "??53")

    def test_candidate_normalizer_allows_strategy_override_per_source(self):
        class PrefixStrategy(DefaultLexiconCandidateStrategy):
            def should_accept(self, literal: str, jyutping: str) -> bool:
                return literal.startswith("AV")

            def build_code(self, literal: str, jyutping: str, *, code: str | None = None) -> str:
                return "AV"

        normalizer = LexiconCandidateNormalizer(strategy=PrefixStrategy())
        candidate = normalizer.normalize_candidate("AV女優", "ei1 wi1 neoi5 jau1", source_id="custom")

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.code, "AV")
        self.assertEqual(candidate.char, "AV女優")

    def test_candidate_normalizer_can_register_strategy_by_source_id(self):
        class PrefixStrategy(DefaultLexiconCandidateStrategy):
            def should_accept(self, literal: str, jyutping: str) -> bool:
                return literal.startswith("AV")

            def build_code(self, literal: str, jyutping: str, *, code: str | None = None) -> str:
                return "AV"

        normalizer = LexiconCandidateNormalizer()
        normalizer.register_strategy("custom", PrefixStrategy())
        candidate = normalizer.normalize_candidate("AV女優", "ei1 wi1 neoi5 jau1", source_id="custom")

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.code, "AV")

    def test_low_rank_source_does_not_add_alternate_claimed_multi_reading(self):
        high = [LexiconCandidate("一行", "jat1 hong4", "30", ("words_hk",))]
        low = [
            LexiconCandidate("一行", "jat1 hang4", "30", ("rime_words",)),
            LexiconCandidate("新詞", "san1 ci4", "30", ("rime_words",)),
        ]
        rows = merge_lexicon_candidates([(90, high), (10, low)])

        by_pair = {(r.char, r.jyutping): r for r in rows}
        self.assertIn(("一行", "jat1 hong4"), by_pair)
        self.assertNotIn(("一行", "jat1 hang4"), by_pair)
        self.assertIn(("新詞", "san1 ci4"), by_pair)

    def test_supplement_sources_are_local_only_raw_files(self):
        manifest = load_manifest(DEFAULT_LEXICON_MANIFEST)
        checked = 0
        for src in manifest:
            if src.get("parser") not in SUPPLEMENT_RAW_PARSERS:
                continue
            checked += 1
            raw_path = str(src.get("raw_path") or "")
            self.assertTrue(raw_path, src["id"])
            self.assertTrue(src.get("local_only"), src["id"])
            self.assertTrue(
                raw_path.startswith("data/lexicon/raw/"),
                f"{src['id']} raw_path must stay maintainer-local: {raw_path}",
            )
            allowlist_path = str(src.get("allowlist_path") or "")
            if allowlist_path:
                self.assertTrue(
                    allowlist_path.startswith("data/lexicon/raw/"),
                    f"{src['id']} allowlist_path must stay maintainer-local: {allowlist_path}",
                )
            reject_path = str(src.get("reject_suffixes_path") or "")
            if reject_path:
                self.assertTrue(
                    reject_path.startswith("data/lexicon/raw/"),
                    f"{src['id']} reject_suffixes_path must stay maintainer-local: {reject_path}",
                )
            lit_path = str(src.get("reject_literals_path") or "")
            if lit_path:
                self.assertTrue(
                    lit_path.startswith("data/lexicon/raw/"),
                    f"{src['id']} reject_literals_path must stay maintainer-local: {lit_path}",
                )
        self.assertGreaterEqual(checked, 5)

    def test_default_manifest_uses_categorized_rime_source_not_legacy_phrase(self):
        manifest = load_manifest(DEFAULT_LEXICON_MANIFEST)
        by_id = {str(src["id"]): src for src in manifest}

        self.assertEqual(by_id["rime_words"]["parser"], "rime_upstream_csv")
        self.assertTrue(
            str(by_id["rime_words"]["raw_path"]).endswith(
                "rime-cantonese-upstream/word.csv"
            )
        )
        self.assertFalse(by_id["rime_phrase"]["enabled_by_default"])


if __name__ == "__main__":
    unittest.main()
