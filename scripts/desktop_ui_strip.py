"""Strip PWA browser-engine dead weight from Desktop UI sidecar (ADR-0068 §13).

Desktop query uses root sidecar lyrics.db + Python API — not sql.js / static
indexes under client/dist-portable. Call after copying dist-portable into the
package; never delete the package-root lyrics.db.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Basename denylist under UI tree only (ADR-0068 §13).
UI_BASENAME_DENY = frozenset(
    {
        "lyrics.db",
        "lyrics.db.gz",
        "static-syn-index.json",
        "static-cilin-syn-index.json",
        "static-ant-index.json",
        "ranking-index.json",
        "rhyme-letter-index.json",
    }
)


def strip_desktop_ui(ui_root: Path) -> list[str]:
    """Remove denylisted files under ui_root. Returns relative paths removed."""
    root = Path(ui_root)
    if not root.is_dir():
        raise FileNotFoundError(f"desktop UI root missing: {root}")

    removed: list[str] = []
    for path in sorted(root.rglob("*"), reverse=True):
        if not path.is_file():
            continue
        if path.name not in UI_BASENAME_DENY:
            continue
        rel = path.relative_to(root).as_posix()
        path.unlink()
        removed.append(rel)
    return removed


def assert_stripped(ui_root: Path) -> None:
    """Fail if any denylisted basename remains under ui_root."""
    root = Path(ui_root)
    if not root.is_dir():
        raise FileNotFoundError(f"desktop UI root missing: {root}")
    leftover = [
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name in UI_BASENAME_DENY
    ]
    if leftover:
        raise AssertionError(
            "Desktop UI still has PWA engine dead weight: " + ", ".join(leftover)
        )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: python scripts/desktop_ui_strip.py <client/dist-portable-in-package>",
            file=sys.stderr,
        )
        return 2
    ui = Path(args[0])
    removed = strip_desktop_ui(ui)
    assert_stripped(ui)
    print(f"Desktop UI strip (ADR-0068 §13): removed {len(removed)} file(s) under {ui}")
    for rel in removed:
        print(f"  - {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
