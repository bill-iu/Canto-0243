"""Shim — moved to tools.campaigns.oneshot._syn_top5000_final_audit_build_meta (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/_syn_top5000_final_audit_build_meta.py moved to tools/campaigns/oneshot/_syn_top5000_final_audit_build_meta.py; "
    "run: python -m tools.campaigns.oneshot._syn_top5000_final_audit_build_meta",
    DeprecationWarning,
    stacklevel=1,
)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
runpy.run_module("tools.campaigns.oneshot._syn_top5000_final_audit_build_meta", run_name="__main__")
