from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKBENCH = ROOT / "client" / "src" / "workbench"


class WorkbenchClientSeamTests(unittest.TestCase):
    def test_workbench_route_does_not_join_query_tabs(self) -> None:
        router = (ROOT / "client" / "src" / "ProductRouter.tsx").read_text(encoding="utf-8")
        page = (WORKBENCH / "WorkbenchPage.tsx").read_text(encoding="utf-8")
        self.assertNotIn("query-tabs", router + page)
        self.assertIn("workbenchPage", (ROOT / "client" / "src" / "app-page.ts").read_text(encoding="utf-8"))

    def test_apply_is_explicit_and_candidate_text_is_horizontal(self) -> None:
        page = (WORKBENCH / "WorkbenchPage.tsx").read_text(encoding="utf-8")
        compare = (WORKBENCH / "ComparePanel.tsx").read_text(encoding="utf-8")
        css = (WORKBENCH / "workbench-page.css").read_text(encoding="utf-8")
        self.assertIn("套用這個選擇", compare)
        self.assertIn("type: 'apply_candidate'", page)
        self.assertIn("writing-mode: horizontal-tb", css)
        self.assertIn("word-break: keep-all", css)

    def test_product_boundary_rejects_auto_lyrics(self) -> None:
        page = (WORKBENCH / "WorkbenchPage.tsx").read_text(encoding="utf-8")
        self.assertIn("不會替你自動填詞", page)
        self.assertNotIn("autoApply", page)
        self.assertNotIn("generateLyrics", page)

    def test_phase1_closeout_guards(self) -> None:
        page = (WORKBENCH / "WorkbenchPage.tsx").read_text(encoding="utf-8")
        cards = (WORKBENCH / "CandidateGrid.tsx").read_text(encoding="utf-8")
        canvas = (WORKBENCH / "SentenceCanvas.tsx").read_text(encoding="utf-8")
        compare = (WORKBENCH / "ComparePanel.tsx").read_text(encoding="utf-8")
        self.assertIn("limit: 120", page)
        self.assertNotIn("type: 'select', start: 0, width: 1", page)
        self.assertIn("放寬後結果", cards)
        self.assertIn("未有足夠近義資料", cards)
        self.assertIn("event.shiftKey", canvas)
        self.assertIn("code-summary", canvas)
        self.assertIn("排序順位", compare)
        self.assertIn("sourceRank", compare)

    def test_phase2_bridge_and_shortcuts(self) -> None:
        page = (WORKBENCH / "WorkbenchPage.tsx").read_text(encoding="utf-8")
        compare = (WORKBENCH / "ComparePanel.tsx").read_text(encoding="utf-8")
        app = (ROOT / "client" / "src" / "App.tsx").read_text(encoding="utf-8")
        detail = (ROOT / "client" / "src" / "entry-detail" / "EntryDetailPanel.tsx").read_text(encoding="utf-8")
        bar = (WORKBENCH / "ConstraintBar.tsx").read_text(encoding="utf-8")
        css = (WORKBENCH / "workbench-page.css").read_text(encoding="utf-8")
        engine = (ROOT / "client" / "src" / "db" / "position-match" / "engine.ts").read_text(encoding="utf-8")
        self.assertIn("consumeIngest", page)
        self.assertIn("lock_selection", page)
        self.assertIn("在搜尋頁查看", compare)
        self.assertIn("放入句格", detail)
        self.assertIn("openSearchTabWithQuery", app)
        self.assertIn("PutInWorkbenchModal", app)
        self.assertIn('value="m1">0243</option>', bar)
        self.assertIn("useState<ReplacementPlanV1['mode']>('m1')", page)
        self.assertIn("var(--ink)", css)
        self.assertNotIn("--wb-ink", css)
        self.assertNotIn("const phonemeSlot = !code ? firstPhonemeAnchorSlot(spec) : null", engine)
        self.assertNotRegex(page, r"consumeIngest[\s\S]{0,400}apply_candidate")


if __name__ == "__main__":
    unittest.main()
