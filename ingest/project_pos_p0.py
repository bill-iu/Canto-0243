"""Shim — moved to tools.campaigns.project_pos_p0 (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings

warnings.warn(
    "ingest.project_pos_p0 moved to tools.campaigns.project_pos_p0; "
    "use: python -m tools.campaigns.project_pos_p0",
    DeprecationWarning,
    stacklevel=2,
)

from tools.campaigns import project_pos_p0 as _impl

if __name__ == "__main__":
    runpy.run_module("tools.campaigns.project_pos_p0", run_name="__main__")
else:
    # Full module swap so tests can patch ingest.project_pos_p0._private
    sys.modules[__name__] = _impl
