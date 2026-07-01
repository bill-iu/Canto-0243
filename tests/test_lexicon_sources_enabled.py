"""words.hk / kaifang lexicon sources (CONTEXT § 詞條源清單)."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.candidates import LexiconCandidate
from app.models.word import Word, WordSource
from ingest.lexicon_build import build_lexicon_words, collect_lexicon_candidates
from ingest.lexicon_sources import ingest_lexicon_json
from ingest.lexicon_truncate import truncate_lexicon_core

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "lexicon" / "sources.yaml"
FIXTURE_MANIFEST = ROOT / "data" / "lexicon" / "fixtures" / "build_sources.yaml"
WORDS_HK_FIXTURE = ROOT / "data" / "lexicon" / "fixtures" / "words_hk_sample.json"
RIME_FIXTURE = ROOT / "data" / "rime" / "fixtures" / "char_sample.csv"


class LexiconSourcesEnabledTests(unittest.TestCase):
    def test_words_hk_and_kaifang_enabled_by_default(self):
        data = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
        by_id = {s["id"]: s for s in data["sources"]}
        self.assertTrue(by_id["words_hk"]["enabled_by_default"])
        self.assertTrue(by_id["kaifang"]["enabled_by_default"])
        self.assertTrue(by_id["words_hk"]["local_only"])
        self.assertTrue(by_id["kaifang"]["local_only"])

    def test_collect_skips_missing_local_only_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rime_dest = root / "data/rime/fixtures/char_sample.csv"
            rime_dest.parent.mkdir(parents=True)
            shutil.copy(RIME_FIXTURE, rime_dest)
            manifest = root / "sources.yaml"
            manifest.write_text(
                """
sources:
  - id: rime
    parser: rime_char
    enabled_by_default: true
    raw_path: data/rime/fixtures/char_sample.csv
    source_rank: 100
  - id: words_hk
    parser: words_hk_wordslist
    enabled_by_default: true
    local_only: true
    raw_path: data/lexicon/raw/words_hk/wordslist.json
    source_rank: 90
""".strip(),
                encoding="utf-8",
            )
            candidates = collect_lexicon_candidates(manifest, repo_root=root)
            sources_seen = {s for c in candidates for s in c.sources}
            self.assertIn("rime", sources_seen)
            self.assertNotIn("words_hk", sources_seen)

    def test_collect_includes_words_hk_from_legacy_raw_when_present(self):
        legacy = ROOT / "data/raw/words.hk/wordslist.json"
        if not legacy.is_file():
            self.skipTest("maintainer-local data/raw/words.hk not present")
        candidates = collect_lexicon_candidates(SOURCES)
        sources_seen = {s for c in candidates for s in c.sources}
        self.assertIn("words_hk", sources_seen)
        self.assertGreater(sum(1 for c in candidates if len(c.char) >= 2), 1000)
        if (ROOT / "data/raw/kaifang").is_dir() and list((ROOT / "data/raw/kaifang").glob("*.txt")):
            self.assertIn("kaifang", sources_seen)

    def test_ingest_lexicon_json_reads_fixture(self):
        out = ingest_lexicon_json(WORDS_HK_FIXTURE, source_id="words_hk")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].char, "香港")

    def test_build_fixture_manifest_includes_words_hk_layer(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        truncate_lexicon_core(session)
        n = build_lexicon_words(session, manifest_path=FIXTURE_MANIFEST)
        session.commit()
        self.assertGreater(n, 14)
        self.assertGreater(session.query(Word).filter(Word.char == "香港").count(), 0)
        wh = session.query(WordSource).filter(WordSource.source == "words_hk").count()
        self.assertGreater(wh, 0)


if __name__ == "__main__":
    unittest.main()
