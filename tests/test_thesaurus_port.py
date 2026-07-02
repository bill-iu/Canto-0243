"""靜態詞林埠 — resolve_admission 風格測試，打公開 Port 介面。"""

import tempfile
import unittest
from pathlib import Path

from app.domain.thesaurus.port import StaticThesaurusPort


class StaticThesaurusPortTests(unittest.TestCase):
    def tearDown(self) -> None:
        from app.domain.thesaurus.port import default_thesaurus_port
        from app.thesaurus.static_index import ensure_thesaurus_loaded, reset_static_indexes_for_tests

        reset_static_indexes_for_tests()
        ensure_thesaurus_loaded(force=True)
        default_thesaurus_port()._loaded = False  # type: ignore[attr-defined]

    def _fixture_port(self) -> StaticThesaurusPort:
        tmp = tempfile.mkdtemp()
        root = Path(tmp)
        cilin = root / "cilin.txt"
        syn = root / "syn.txt"
        ant = root / "ant.txt"
        cilin.write_text("Aa01A01= 開心 快樂 高興\n", encoding="utf-8")
        syn.write_text("Bb01= 愉快 欣喜\n", encoding="utf-8")
        ant.write_text("開心 難過 悲傷\n前——後\n", encoding="utf-8")
        return StaticThesaurusPort(
            cilin_path=str(cilin),
            thesaurus_syn_path=str(syn),
            thesaurus_ant_path=str(ant),
        )

    def test_merged_synonyms_combine_cilin_and_guotong(self):
        port = self._fixture_port()
        merged = port.get_synonyms("開心")
        self.assertIn("快樂", merged)
        self.assertIn("欣喜", port.get_synonyms("愉快"))

    def test_source_specific_syn_getters(self):
        port = self._fixture_port()
        self.assertIn("快樂", port.get_cilin_synonyms("開心"))
        self.assertNotIn("欣喜", port.get_cilin_synonyms("愉快"))
        self.assertIn("欣喜", port.get_guotong_synonyms("愉快"))

    def test_iter_literal_heads_unions_sources(self):
        port = self._fixture_port()
        heads = set(port.iter_literal_heads())
        self.assertIn("開心", heads)
        self.assertIn("愉快", heads)
        self.assertIn("前", heads)

    def test_custom_load_survives_static_get_synonyms(self):
        """Custom guotong ant must not be wiped when static_index.get_synonyms runs."""
        import tempfile
        from pathlib import Path

        import app.thesaurus.static_index as si

        si.reset_static_indexes_for_tests()
        with tempfile.TemporaryDirectory() as tmp:
            ant = Path(tmp) / "ant.txt"
            ant.write_text("開心 難過 悲傷\n", encoding="utf-8")
            port = StaticThesaurusPort(thesaurus_ant_path=str(ant), auto_load=True)
            self.assertIn("開心", port.get_antonyms("悲傷"))
            si.get_synonyms("快樂")
            self.assertIn("開心", port.get_antonyms("悲傷"))

    def test_antonyms_and_edges(self):
        port = self._fixture_port()
        ants = port.get_antonyms("開心")
        self.assertGreaterEqual(len(ants), 1)
        pairs = set(port.iter_antonym_edges())
        self.assertTrue(any(h == "開心" and t in ants for h, t in pairs))
        self.assertIn(("前", "後"), pairs)


if __name__ == "__main__":
    unittest.main()
