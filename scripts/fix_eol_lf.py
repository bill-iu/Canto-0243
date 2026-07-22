#!/usr/bin/env python3
"""Rewrite CRLF/CR → LF in text files. Used by .githooks/pre-commit (ADR-0063)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Skip obvious binaries by extension (gitattributes is the SSOT; this is a safety net).
_BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".wasm",
    ".db", ".sqlite", ".sqlite3",
    ".zip", ".gz", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".pdf", ".mp3", ".mp4",
    ".pyc", ".pyd",
}


def _is_probably_binary(path: Path, sample: bytes) -> bool:
    if path.suffix.lower() in _BINARY_EXT:
        return True
    if b"\0" in sample:
        return True
    return False


def fix_bytes(data: bytes) -> bytes | None:
    """Return LF-normalized bytes, or None if unchanged / binary skip."""
    if b"\0" in data[:8192]:
        return None
    if b"\r" not in data:
        return None
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def fix_path(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if _is_probably_binary(path, data[:8192]):
        return False
    fixed = fix_bytes(data)
    if fixed is None:
        return False
    path.write_bytes(fixed)
    return True


def staged_paths() -> list[Path]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=REPO,
    )
    if not out:
        return []
    return [REPO / p for p in out.decode("utf-8", errors="surrogateescape").split("\0") if p]


def fix_staged() -> int:
    changed: list[Path] = []
    for path in staged_paths():
        if fix_path(path):
            changed.append(path)
    if not changed:
        return 0
    rel = [str(p.relative_to(REPO)).replace("\\", "/") for p in changed]
    subprocess.check_call(["git", "add", "--", *rel], cwd=REPO)
    print(f"fix_eol_lf: normalized {len(changed)} staged file(s) to LF")
    return 0


def _self_check() -> None:
    assert fix_bytes(b"a\r\nb\r\n") == b"a\nb\n"
    assert fix_bytes(b"a\nb\n") is None
    assert fix_bytes(b"a\rb\n") == b"a\nb\n"
    assert fix_bytes(b"\0bin") is None
    print("fix_eol_lf self-check ok")


def main(argv: list[str]) -> int:
    if argv == ["--self-check"]:
        _self_check()
        return 0
    if argv == ["--staged"] or argv == []:
        return fix_staged()
    n = 0
    for raw in argv:
        p = Path(raw)
        if not p.is_absolute():
            p = REPO / p
        if fix_path(p):
            n += 1
            print(f"LF: {p.relative_to(REPO)}")
    return 0 if n or argv else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
