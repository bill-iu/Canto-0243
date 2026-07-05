"""Simulate CI: no .env.local side effects, fixture only."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.pop("DATABASE_URL", None)
os.environ["READINESS_GATE_ENFORCE"] = "0"
# Re-import would be needed; run subprocess instead