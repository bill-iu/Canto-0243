"""Shim — moved to tools.campaigns.oneshot._len4_b02_draft (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/_len4_b02_draft.py moved to tools/campaigns/oneshot/_len4_b02_draft.py; "
    "run: python -m tools.campaigns.oneshot._len4_b02_draft",
    DeprecationWarning,
    stacklevel=1,
)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
runpy.run_module("tools.campaigns.oneshot._len4_b02_draft", run_name="__main__")
