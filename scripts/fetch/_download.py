"""Shared HTTP download helpers for fetch scripts."""

from __future__ import annotations

import urllib.request
from pathlib import Path


def download_file(url: str, dest: Path, *, label: str | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    name = label or dest.name
    print(f"Downloading {name} ...")
    print(f"  {url}")
    urllib.request.urlretrieve(url, dest)
    size = dest.stat().st_size
    print(f"Wrote {dest} ({size:,} bytes)")
    return dest
