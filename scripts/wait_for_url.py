#!/usr/bin/env python3
"""Shim — implementation in app.launch.wait_for_url (ADR-0068)."""
from __future__ import annotations

from app.launch.wait_for_url import main

if __name__ == "__main__":
    raise SystemExit(main())
