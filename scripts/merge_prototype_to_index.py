"""One-time migration: replace index.html inline CSS with open-design.css + shell.css links.

Completed in E2 phase 1; prototype.html source removed. Kept for reference only.
"""
import sys
from pathlib import Path

if __name__ == "__main__":
    print("merge_prototype_to_index.py is a completed one-time migration.", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parents[1]
src_path = ROOT / "shared" / "prototype.html"
out_path = ROOT / "shared" / "index.html"
