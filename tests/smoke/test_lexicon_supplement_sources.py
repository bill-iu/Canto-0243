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
    ingest_hsk30_wordlist,
    ingest_rime_words_yaml,
    resolve_generated_jyutping,
)
from ingest.syn_ant_manifest import load_manifest


SUPPLEMENT_RAW_PARSERS = {
    "hsk30_wordlist",
    "kaifang_txt",
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
        self.assertGreaterEqual(checked, 4)


if __name__ == "__main__":
    unittest.main()
