"""Shim — moved to tools.campaigns.project_pos_cleanup (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings

warnings.warn(
    "ingest.project_pos_cleanup moved to tools.campaigns.project_pos_cleanup; "
    "use: python -m tools.campaigns.project_pos_cleanup",
    DeprecationWarning,
    stacklevel=2,
)

from tools.campaigns import project_pos_cleanup as _impl

if __name__ == "__main__":
    runpy.run_module("tools.campaigns.project_pos_cleanup", run_name="__main__")
else:
    # Full module swap so tests can patch ingest.project_pos_cleanup._private
    sys.modules[__name__] = _impl
