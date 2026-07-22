from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class WorkbenchReportedRegressionTests(unittest.TestCase):
    def test_pos_filter_is_one_left_drawer_at_every_width(self) -> None:
        css = read("client/src/pos/pos-filter.css")
        self.assertRegex(css, r"(?s)\.pos-filter__panel\s*\{[^}]*position:\s*fixed")
        self.assertRegex(css, r"(?s)\.pos-filter__panel\s*\{[^}]*left:\s*0")
        self.assertNotIn("position: absolute", css)
        self.assertNotRegex(css, r"(?s)@media[^}]+\.pos-filter__panel[^}]+bottom:\s*0")

    def test_pos_filter_drawer_has_dialog_and_focus_contract(self) -> None:
        control = read("client/src/pos/PosFilterControl.tsx")
        self.assertIn('role="dialog"', control)
        self.assertIn('aria-modal="true"', control)
        self.assertIn("createPortal", control)
        self.assertIn("triggerRef", control)
        self.assertIn("focusable", control)

    def test_position_copy_and_whole_toggle_are_multi_select_friendly(self) -> None:
        span = read("client/src/workbench/replacement-span.ts")
        bar = read("client/src/workbench/ConstraintBar.tsx")
        self.assertNotIn("只要求", span)
        self.assertNotIn("disabled={picks.whole}", bar)

    def test_surface_readings_do_not_become_hidden_tone_constraints(self) -> None:
        page = read("client/src/workbench/WorkbenchPage.tsx")
        self.assertNotIn("if (slot.code && !slots.some", page)

    def test_changing_selected_reading_rebuilds_phoneme_anchors(self) -> None:
        page = read("client/src/workbench/WorkbenchPage.tsx")
        reducer = read("client/src/workbench/session/reducer.ts")
        phoneme = read("client/src/workbench/session/phoneme.ts")
        span = read("client/src/workbench/replacement-span.ts")
        self.assertIn("handleChooseReading", page)
        self.assertRegex(reducer, r"case 'choose_reading':[\s\S]{0,260}withDraftAction")
        self.assertIn("draft = syncPhonemeFromConstraints(draft, next.constraints)", reducer)
        self.assertIn("buildPhonemeAnchors(", phoneme)
        self.assertIn("refJyutping", span)

    def test_workbench_chinese_serif_uses_complete_local_family_first(self) -> None:
        build = read("client/scripts/build-fonts.ts")
        critical = read("client/src/critical-display-text.ts")
        intro = read("client/src/workbench/intro-copy.ts")
        self.assertIn("criticalDisplayText", build)
        for char in "句格工作台拆解萬種可能":
            self.assertIn(char, critical + intro)


if __name__ == "__main__":
    unittest.main()
