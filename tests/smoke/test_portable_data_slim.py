"""C11-B: portable data denylist slim."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.portable_data_slim import (
    REQUIRED_RUNTIME_RELPATHS,
    assert_runtime_data,
    count_files,
    data_copy_ignore,
    slim_portable_data,
)


class PortableDataSlimTests(unittest.TestCase):
    def test_data_copy_ignore(self) -> None:
        skipped = data_copy_ignore(
            "data",
            ["cilin", "audit", "fixtures", "raw", "pos", "essay", "proposals", "project"],
        )
        self.assertEqual(
            set(skipped), {"audit", "fixtures", "raw", "pos", "proposals", "project"}
        )

    def test_slim_keeps_runtime_drops_junk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            for rel in REQUIRED_RUNTIME_RELPATHS:
                path = data / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            junk_dir = data / "pos" / "audit"
            junk_dir.mkdir(parents=True)
            (junk_dir / "sample.tsv").write_text("x\n", encoding="utf-8")
            fixtures = data / "syn_ant" / "fixtures"
            fixtures.mkdir(parents=True)
            (fixtures / "f.tsv").write_text("x\n", encoding="utf-8")
            (data / "syn_ant" / "campaign_top5000.tsv").write_text("x\n", encoding="utf-8")
            (data / "syn_ant" / "project_antonyms.tsv").write_text("x\n", encoding="utf-8")
            proj = data / "syn_ant" / "project"
            proj.mkdir(parents=True)
            (proj / "project_synonyms.tsv").write_text("x\n", encoding="utf-8")
            (data / "antonym" / "antisem.txt").parent.mkdir(parents=True, exist_ok=True)
            (data / "antonym" / "antisem.txt").write_text("x\n", encoding="utf-8")

            before = count_files(data)
            stats = slim_portable_data(data)
            self.assertGreater(stats["data_files_removed"], 0)
            self.assertFalse(junk_dir.exists())
            self.assertFalse(fixtures.exists())
            self.assertFalse(proj.exists())
            self.assertFalse((data / "syn_ant" / "campaign_top5000.tsv").exists())
            self.assertFalse((data / "syn_ant" / "project_antonyms.tsv").exists())
            self.assertFalse((data / "antonym" / "antisem.txt").exists())
            assert_runtime_data(data)
            self.assertEqual(stats["data_files_after"], count_files(data))
            self.assertLess(stats["data_files_after"], before)


if __name__ == "__main__":
    unittest.main()
