"""Installed app code must read ranking signals from the bound sidecar payload."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RankingPayloadLayoutTests(unittest.TestCase):
    def test_relocated_installed_app_keeps_payload_ranking_and_reading_signals(self):
        with TemporaryDirectory() as tmp:
            site = Path(tmp) / "site-packages"
            shutil.copytree(ROOT / "app", site / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            # -I excludes checkout/PYTHONPATH; only the relocated package is added.
            # Data stays in the separate bound payload, as in a Desktop install.
            code = r'''
import json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
from app.lexicon import essay_index as essay, curated_index as curated
from app.lexicon.compound_synonyms import load_compound_synonyms
from app.lexicon.compound_antonyms import load_compound_antonyms
from app.lexicon.word_usage import load_word_usage,word_usage_sort_key
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.domain.lexicon.ranking import search_result_sort_key
words=["已經","覺得","女仔","這些","那麼"]
rows=[SimpleNamespace(char=char,jyutping="") for char in words]
result={
    "module":essay.__file__,
    "essay_path":str(essay.DEFAULT_ESSAY_PATH),
    "essay_rows":essay.load_essay_corpus(),
    "essay_literals":len(essay._freq_by_char),
    "essay_frequency":essay.get_essay_frequency("覺得"),
    "curated_path":str(curated.DEFAULT_CURATED_PATH),
    "curated_count":curated.load_curated_common(),
    "usage_count":len(load_word_usage()),
    "usage_grade":word_usage_sort_key("覺得")[0],
    "reading_grade":pron_rank_sort_value_for_word("社會保障","se5 wui2 bou2 zoeng3"),
    "compound_syn_count":len(load_compound_synonyms()),
    "compound_ant_count":len(load_compound_antonyms()),
    "order":[row.char for row in sorted(rows,key=search_result_sort_key)],
}
print(json.dumps(result,ensure_ascii=False))
'''
            env = dict(os.environ, CANTO_PAYLOAD_ROOT=str(ROOT))
            run = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", "-c", code, str(site)],
                cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertTrue(Path(result["module"]).is_relative_to(site))
            self.assertEqual(Path(result["essay_path"]), ROOT / "data/essay/essay-cantonese.txt")
            self.assertEqual(result["essay_rows"], 266904)
            self.assertEqual(result["essay_literals"], 266884)
            self.assertEqual(result["essay_frequency"], 398483)
            self.assertEqual(Path(result["curated_path"]), ROOT / "data/lexicon/curated_common.txt")
            self.assertEqual(result["curated_count"], 5)
            usage_meta = json.loads((ROOT / "data/lexicon/word_usage.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(result["usage_count"], usage_meta["graded_literals"])
            self.assertEqual(result["usage_grade"], 0)
            self.assertEqual(result["reading_grade"], 0)
            self.assertGreater(result["compound_syn_count"], 0)
            self.assertGreater(result["compound_ant_count"], 0)
            self.assertEqual(result["order"], ["已經", "覺得", "女仔", "那麼", "這些"])


if __name__ == "__main__":
    unittest.main()
