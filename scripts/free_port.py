#!/usr/bin/env python3
"""Shim — implementation in app.launch.free_port (ADR-0068)."""
from __future__ import annotations

from app.launch.free_port import main

if __name__ == "__main__":
    raise SystemExit(main())
