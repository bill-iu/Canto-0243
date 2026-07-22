"""Shim — moved to tools.campaigns.project_pos_audit (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings

warnings.warn(
    "ingest.project_pos_audit moved to tools.campaigns.project_pos_audit; "
    "use: python -m tools.campaigns.project_pos_audit",
    DeprecationWarning,
    stacklevel=2,
)

from tools.campaigns import project_pos_audit as _impl

if __name__ == "__main__":
    runpy.run_module("tools.campaigns.project_pos_audit", run_name="__main__")
else:
    # Full module swap so tests can patch ingest.project_pos_audit._private
    sys.modules[__name__] = _impl
