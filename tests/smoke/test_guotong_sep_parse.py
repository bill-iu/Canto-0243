"""guotong ant/syn lines use ASCII `--`; loader must split them."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.thesaurus.static_index import (
    get_antonyms,
    load_thesaurus_dicts,
    mark_thesaurus_loaded,
    reset_static_indexes_for_tests,
)


class GuotongSepParseTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_static_indexes_for_tests()

    def test_ascii_double_hyphen_and_dash_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            syn = root / "syn.txt"
            ant = root / "ant.txt"
            syn.write_text("開心 快樂\n", encoding="utf-8")
            # separators observed in dict_antonym.txt
            ant.write_text(
                "\n".join(
                    [
                        "死--活",
                        "前——後",
                        "公──私",
                        "美麗—醜陋",
                        "寬闊―狹窄",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            reset_static_indexes_for_tests()
            load_thesaurus_dicts(str(syn), str(ant))
            mark_thesaurus_loaded()

            self.assertIn("活", get_antonyms("死"))
            self.assertIn("後", get_antonyms("前"))
            self.assertIn("私", get_antonyms("公"))
            self.assertIn("醜陋", get_antonyms("美麗"))
            self.assertIn("狹窄", get_antonyms("寬闊"))

    def test_bundled_antonym_ascii_hyphen_coverage(self) -> None:
        """Regression: real dict has ~17k `--` lines that were previously skipped."""
        reset_static_indexes_for_tests()
        load_thesaurus_dicts()
        # known `--` rows from dict_antonym.txt
        self.assertIn("活", get_antonyms("死"))
        self.assertIn("慢", get_antonyms("快"))
        # still keep em-dash rows
        self.assertIn("後", get_antonyms("前"))


if __name__ == "__main__":
    unittest.main()
