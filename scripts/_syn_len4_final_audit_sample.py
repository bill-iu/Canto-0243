"""Shim — moved to tools.campaigns.oneshot._syn_len4_final_audit_sample (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/_syn_len4_final_audit_sample.py moved to tools/campaigns/oneshot/_syn_len4_final_audit_sample.py; "
    "run: python -m tools.campaigns.oneshot._syn_len4_final_audit_sample",
    DeprecationWarning,
    stacklevel=1,
)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
runpy.run_module("tools.campaigns.oneshot._syn_len4_final_audit_sample", run_name="__main__")
