"""Shim — moved to tools.campaigns.project_pos_iwp (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings

warnings.warn(
    "ingest.project_pos_iwp moved to tools.campaigns.project_pos_iwp; "
    "use: python -m tools.campaigns.project_pos_iwp",
    DeprecationWarning,
    stacklevel=2,
)

from tools.campaigns import project_pos_iwp as _impl

if __name__ == "__main__":
    runpy.run_module("tools.campaigns.project_pos_iwp", run_name="__main__")
else:
    # Full module swap so tests can patch ingest.project_pos_iwp._private
    sys.modules[__name__] = _impl
