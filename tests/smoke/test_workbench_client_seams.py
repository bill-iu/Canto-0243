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

    def test_fresh_workbench_route_reveals_editable_shell_before_lexicon_ready(self) -> None:
        page = (WORKBENCH / "WorkbenchPage.tsx").read_text(encoding="utf-8")
        self.assertIn("revealPwaShell", page)
        self.assertRegex(page, r"useEffect\(\(\) => \{[\s\S]{0,160}revealPwaShell\(\)")

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
        self.assertIn("WORKBENCH_CANDIDATE_PAGE_SIZE", page)
        self.assertNotIn("limit: 120", page)
        self.assertNotIn("type: 'select', start: 0, width: 1", page)
        self.assertIn("載入更多", cards)
        self.assertIn("池內", cards)
        self.assertIn("放寬後結果", cards)
        self.assertIn("未有足夠近義資料", cards)
        self.assertIn("onToggleLock", canvas)
        self.assertIn("is-in-span", canvas)
        self.assertIn("slot-reading-footer", canvas)
        self.assertIn("is-code-surface", canvas)
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
        self.assertIn("toggleLockKeepingSpan", page)
        self.assertNotIn("slot.locked && slot.surface", page)
        self.assertIn("整段押韻", bar)
        self.assertIn("整段同聲母", bar)
        self.assertNotIn("末格同韻", bar)
        self.assertIn("在搜尋頁查看", compare)
        self.assertIn("放入句格", detail)
        self.assertIn("openSearchTabWithQuery", app)
        self.assertIn("PutInWorkbenchModal", app)
        self.assertIn("ModeMenu", page)
        self.assertIn("HeaderHero", page)
        self.assertIn("BrandLogo", page)
        self.assertNotIn("返回查韻", page)
        self.assertIn("consumeNavigate", app)
        self.assertIn("writeNavigate", page)
        self.assertIn('value="m1">0243</option>', bar)
        self.assertIn("同音（預設）", bar)
        self.assertIn("指定碼", bar)
        self.assertIn("useState<ReplacementPlanV1['mode']>('m1')", page)
        self.assertIn("var(--ink)", css)
        self.assertNotIn("--wb-ink", css)
        self.assertIn("workbench-route", css)
        self.assertNotIn("const phonemeSlot = !code ? firstPhonemeAnchorSlot(spec) : null", engine)
        self.assertNotRegex(page, r"consumeIngest[\s\S]{0,400}apply_candidate")


if __name__ == "__main__":
    unittest.main()
