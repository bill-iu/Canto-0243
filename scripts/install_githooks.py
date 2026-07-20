#!/usr/bin/env python3
"""Copy committed hooks into .git/hooks (no git config changes; ADR-0063)."""

from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / ".githooks"
DST = REPO / ".git" / "hooks"


def main() -> int:
    if not (REPO / ".git").exists():
        print("install_githooks: not a git checkout", file=sys.stderr)
        return 1
    DST.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in sorted(SRC.iterdir()):
        if not src.is_file() or src.name.startswith("."):
            continue
        dest = DST / src.name
        shutil.copy2(src, dest)
        mode = dest.stat().st_mode
        dest.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        copied += 1
        print(f"installed {dest.relative_to(REPO)}")
    if not copied:
        print("install_githooks: nothing in .githooks/", file=sys.stderr)
        return 1
    print("ok — pre-commit will normalize CRLF → LF on commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
