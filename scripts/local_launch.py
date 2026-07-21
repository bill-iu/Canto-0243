#!/usr/bin/env python3
"""Shim — implementation in app.launch.local_launch (ADR-0068)."""
from __future__ import annotations

from app.launch.local_launch import main

if __name__ == "__main__":
    raise SystemExit(main())
