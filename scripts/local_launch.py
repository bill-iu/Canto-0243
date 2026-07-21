#!/usr/bin/env python3
"""Shim — implementation in app.launch.local_launch (ADR-0068)."""
from __future__ import annotations

import sys
from pathlib import Path

# Dev: `python scripts/local_launch.py` does not put repo root on sys.path.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.launch.local_launch import main

if __name__ == "__main__":
    raise SystemExit(main())
