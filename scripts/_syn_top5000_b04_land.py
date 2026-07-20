"""Shim — moved to tools.campaigns.oneshot._syn_top5000_b04_land (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/_syn_top5000_b04_land.py moved to tools/campaigns/oneshot/_syn_top5000_b04_land.py; "
    "run: python -m tools.campaigns.oneshot._syn_top5000_b04_land",
    DeprecationWarning,
    stacklevel=1,
)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
runpy.run_module("tools.campaigns.oneshot._syn_top5000_b04_land", run_name="__main__")
