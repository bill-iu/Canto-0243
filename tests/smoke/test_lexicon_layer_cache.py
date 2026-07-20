"""C3: per-source lexicon layer cache hit/miss."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_layer_cache import (
    fingerprint_source,
    layer_cache_enabled,
    load_or_ingest_source,
)


class LexiconLayerCacheTests(unittest.TestCase):
    def test_env_disable(self) -> None:
        with mock.patch.dict("os.environ", {"LEXICON_LAYER_CACHE": "0"}):
            self.assertFalse(layer_cache_enabled())
        self.assertFalse(layer_cache_enabled(explicit=False))
        self.assertTrue(layer_cache_enabled(explicit=True))

    def test_hit_after_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            raw = cache_dir / "raw.txt"
            raw.write_text("dummy", encoding="utf-8")
            src = {
                "id": "fixture",
                "parser": "lexicon_json",
                "source_rank": 20,
                "raw_path": str(raw),
            }
            cand = [LexiconCandidate("香", "hoeng1", "1", ("fixture",))]
            with mock.patch(
                "ingest.lexicon_layer_cache.ingest_source",
                return_value=cand,
            ) as ingest:
                with mock.patch(
                    "ingest.lexicon_layer_cache.source_input_paths",
                    return_value=[raw],
                ):
                    first, st1 = load_or_ingest_source(
                        src, use_cache=True, cache_dir=cache_dir
                    )
                    second, st2 = load_or_ingest_source(
                        src, use_cache=True, cache_dir=cache_dir
                    )
            self.assertEqual(st1, "miss")
            self.assertEqual(st2, "hit")
            self.assertEqual(ingest.call_count, 1)
            self.assertEqual(first, cand)
            self.assertEqual(second, cand)

    def test_fingerprint_changes_with_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "a.txt"
            raw.write_text("one", encoding="utf-8")
            src = {"id": "x", "parser": "p", "raw_path": str(raw)}
            with mock.patch(
                "ingest.lexicon_layer_cache.source_input_paths",
                return_value=[raw],
            ):
                fp1 = fingerprint_source(src)
                raw.write_text("two", encoding="utf-8")
                fp2 = fingerprint_source(src)
            self.assertNotEqual(fp1, fp2)


if __name__ == "__main__":
    unittest.main()
