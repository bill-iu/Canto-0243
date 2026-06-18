"""近反義模式 dispatch table — step order and first-match (ADR #4)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.query_mode_dispatch import SYN_MODE_STEPS, dispatch_syn_mode


class SynModeStepsOrderTests(unittest.TestCase):
    def test_step_names_frozen(self):
        self.assertEqual(
            [name for name, _, _ in SYN_MODE_STEPS],
            ["jyutping_reject", "relation_redirect", "pool_page"],
        )

    def test_jyutping_reject_before_relation_redirect(self):
        ctx = MagicMock(mode="syn")
        matched = [name for name, pred, _ in SYN_MODE_STEPS if pred("syut", ctx)]
        self.assertEqual(matched[:1], ["jyutping_reject"])

    def test_relation_redirect_before_pool_page(self):
        ctx = MagicMock(mode="syn")
        matched = [name for name, pred, _ in SYN_MODE_STEPS if pred("!開心", ctx)]
        self.assertEqual(matched[:1], ["relation_redirect"])

    def test_plain_chars_hit_pool_page_only(self):
        ctx = MagicMock(mode="syn")
        matched = [name for name, pred, _ in SYN_MODE_STEPS if pred("開心", ctx)]
        self.assertEqual(matched, ["pool_page"])


class DispatchSynModeDelegationTests(unittest.TestCase):
    def test_delegates_to_first_matching_handler(self):
        engine = MagicMock()
        ctx = MagicMock()
        expected = MagicMock()
        engine._dispatch.return_value = expected

        calls: list[str] = []

        def track(name):
            def handler(c, q, e):
                calls.append(name)
                return MagicMock(name=f"result_{name}")

            return handler

        patched = tuple(
            (name, pred, track(name) if name == "relation_redirect" else h)
            for name, pred, h in SYN_MODE_STEPS
        )

        with patch(
            "app.services.query_mode_dispatch.SYN_MODE_STEPS", patched
        ):
            dispatch_syn_mode(ctx, "!開心", engine)

        self.assertEqual(calls, ["relation_redirect"])


if __name__ == "__main__":
    unittest.main()
