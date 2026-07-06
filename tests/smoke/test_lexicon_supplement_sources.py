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
    ingest_rime_phrase_yaml,
    ingest_rime_words_yaml,
    resolve_generated_jyutping,
)
from ingest.syn_ant_manifest import load_manifest


SUPPLEMENT_RAW_PARSERS = {
    "hsk30_wordlist",
    "kaifang_txt",
    "rime_phrase_yaml",
    "rime_words_yaml",
    "words_hk_wordslist",
}


class LexiconSupplementSourceTests(unittest.TestCase):
    def test_hsk30_wordlist_converts_traditional_and_uses_pycantonese(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "wordlist.txt"
            path.write_text("后台\n一级词汇表\n", encoding="utf-8")

            def fake_reading(text: str) -> str | None:
                return "hau6 toi4" if text == "後臺" else None

            with patch("ingest.lexicon_sources._full_pycantonese_reading", side_effect=fake_reading):
                rows = ingest_hsk30_wordlist(path, source_id="hsk30")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].char, "後臺")
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
        self.assertGreaterEqual(checked, 5)


if __name__ == "__main__":
    unittest.main()
