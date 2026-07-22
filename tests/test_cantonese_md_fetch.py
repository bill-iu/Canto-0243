from __future__ import annotations

import io
import unittest
import zipfile

from scripts.fetch.fetch_cantonese_md_lexicon import _load_rows


def _archive(content_type: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            f"repo/src/contents/{content_type}/entry.md",
            "---\nterm: 測試\ntermJyutping: cak1 si3\nanswer: 答案\nanswerJyutping: daap3 on3\n---\n",
        )
    return buffer.getvalue()


class TestCantoneseMdFetch(unittest.TestCase):
    def test_structured_content_type_is_preserved(self) -> None:
        rows = _load_rows(_archive("idioms"))
        self.assertEqual(rows[0]["contentType"], "idioms")

    def test_unknown_content_type_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unmapped"):
            _load_rows(_archive("slangs"))


if __name__ == "__main__":
    unittest.main()
