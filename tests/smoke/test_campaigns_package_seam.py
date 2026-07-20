"""C8: 戰役工具 live under tools.campaigns; ingest shims swap modules."""
from __future__ import annotations

import unittest


class CampaignsPackageSeamTests(unittest.TestCase):
    def test_tools_campaigns_import(self):
        from tools.campaigns._repo import REPO_ROOT
        from tools.campaigns import project_pos_p0

        self.assertTrue((REPO_ROOT / "CONTEXT.md").is_file())
        self.assertTrue(str(project_pos_p0.__file__).replace("\\", "/").endswith(
            "tools/campaigns/project_pos_p0.py"
        ))

    def test_ingest_shim_swaps_module(self):
        import ingest.project_pos_p0 as m

        self.assertTrue(m.__name__.endswith("project_pos_p0"))
        self.assertIn("tools", m.__file__.replace("\\", "/"))
        self.assertTrue(hasattr(m, "p0_status"))


if __name__ == "__main__":
    unittest.main()
