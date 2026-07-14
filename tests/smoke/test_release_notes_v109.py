"""v1.0.9 release notes：高頻 campaign 發版聲明契約（WP-11）。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "docs" / "release-notes" / "v1.0.9.md"


class ReleaseNotesV109Tests(unittest.TestCase):
    def test_notes_exist_with_campaign_claim_and_user_fixes(self) -> None:
        self.assertTrue(NOTES.is_file(), f"missing {NOTES}")
        text = NOTES.read_text(encoding="utf-8")
        # 產品 headline + 已裁定定義（grill A+B）
        self.assertIn("v1.0.9", text)
        self.assertRegex(text, r"高頻|campaign")
        self.assertIn("已裁定", text)
        self.assertIn("有近無直連反", text)
        self.assertIn("accepted", text)
        self.assertIn("no_natural", text)
        self.assertIn("唔", text)  # 不宣稱全詞庫
        self.assertRegex(text, r"全詞庫|每詞")
        # 次要使用者可見 fix
        self.assertRegex(text, r"lookup|缺字|字面")
        self.assertRegex(text, r"PWA|分頁|title|標題")


if __name__ == "__main__":
    unittest.main()
