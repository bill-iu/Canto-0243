"""lexicon_version SSOT for Portable menu meta."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from app.lexicon_version import lexicon_version


class LexiconVersionTest(unittest.TestCase):
    def test_readme_fallback(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LEXICON_VERSION", None)
            os.environ.pop("VITE_LEXICON_VERSION", None)
            self.assertEqual(lexicon_version(), "v1.0.9")

    def test_env_overrides(self):
        with mock.patch.dict(os.environ, {"LEXICON_VERSION": "v1.2.3"}, clear=False):
            self.assertEqual(lexicon_version(), "v1.2.3")

    def test_env_adds_v_prefix(self):
        with mock.patch.dict(os.environ, {"LEXICON_VERSION": "1.2.3"}, clear=False):
            self.assertEqual(lexicon_version(), "v1.2.3")


if __name__ == "__main__":
    unittest.main()
