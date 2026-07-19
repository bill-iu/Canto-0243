#!/usr/bin/env python3
"""Write portable-manifest.json into a staged portable OutDir (before zip/tar)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.portable_update import write_manifest  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Stamp 套件發佈指紋 into portable OutDir")
    p.add_argument("--root", type=Path, required=True, help="Staged portable directory")
    p.add_argument("--tag", required=True, help="Release tag, e.g. v1.2.0")
    p.add_argument(
        "--platform",
        required=True,
        choices=("windows", "macos-x86_64", "macos-arm64"),
    )
    p.add_argument(
        "--sidecar",
        type=Path,
        default=None,
        help="Also write release asset JSON (e.g. dist/portable-manifest-windows.json)",
    )
    args = p.parse_args()
    fp = write_manifest(args.root, tag=args.tag, platform=args.platform, sidecar=args.sidecar)
    print(f"portable-manifest: tag={fp['tag']} platform={fp['platform']}")
    print(f"  lyrics_sha256={fp['lyrics_sha256'][:16]}…")
    print(f"  package_digest={fp['package_digest'][:16]}…")
    if args.sidecar:
        print(f"  sidecar={args.sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
