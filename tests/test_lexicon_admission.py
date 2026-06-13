"""Phase C #4: 詞庫埠收錄決策 — resolve_admission 集中規則。"""

import unittest
from unittest.mock import patch

from app.lexicon.static_index import LexiconEntry
from app.domain.lexicon.admission import AdmissionSource, resolve_admission


class FakeLexiconPort:
    def __init__(self, entries_by_char):
        self._entries = entries_by_char

    def ensure_loaded(self) -> None:
        pass

    def get_entries(self, char: str):
        return list(self._entries.get(char, []))


class ResolveAdmissionTests(unittest.TestCase):
    def test_multi_char_lexicon_hit(self):
        port = FakeLexiconPort(
            {
                "香港": [
                    LexiconEntry(char="香港", jyutping="hoeng1 gong2", code="12"),
                ],
            }
        )
        result = resolve_admission("香港", lexicon=port)
        self.assertEqual(result.source, AdmissionSource.MULTI_CHAR_LEXICON)
        self.assertTrue(result.can_inject)
        self.assertEqual(len(result.entries), 1)

    def test_multi_char_miss_falls_back_to_syllable_compose(self):
        port = FakeLexiconPort({})
        composed = [LexiconEntry(char="你好", jyutping="nei5 hou2", code="45")]
        with patch(
            "app.domain.lexicon.admission.compose_lexicon_entries_from_rime",
            return_value=composed,
        ):
            result = resolve_admission("你好", lexicon=port)
        self.assertEqual(result.source, AdmissionSource.SYLLABLE_COMPOSE)
        self.assertEqual(result.entries, composed)

    def test_multi_char_miss_without_compose_cannot_inject(self):
        port = FakeLexiconPort({})
        with patch(
            "app.domain.lexicon.admission.compose_lexicon_entries_from_rime",
            return_value=[],
        ):
            result = resolve_admission("走你好", lexicon=port)
        self.assertEqual(result.source, AdmissionSource.NONE)
        self.assertFalse(result.can_inject)

    def test_single_char_from_port(self):
        port = FakeLexiconPort({"你": [LexiconEntry(char="你", jyutping="nei5", code="4")]})
        result = resolve_admission("你", lexicon=port)
        self.assertEqual(result.source, AdmissionSource.SINGLE_CHAR_RIME)
        self.assertEqual(result.entries[0].jyutping, "nei5")


if __name__ == "__main__":
    unittest.main()
