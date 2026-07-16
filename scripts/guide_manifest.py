"""搜尋教學 execution manifest — `shared/guide-i18n.mjs` 是唯一來源。"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "shared" / "guide-i18n.mjs"

MANIFEST_EXAMPLE_RE = re.compile(
    r"\{\s*query:\s*(['\"])((?:\\.|(?!\1).)*)\1,\s*mode:\s*(['\"])((?:\\.|(?!\3).)*)\3\s*\}"
)


def load_manifest_examples() -> list[tuple[str, str]]:
    import json

    text = MANIFEST_PATH.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for m in MANIFEST_EXAMPLE_RE.finditer(text):
        q = json.loads(m.group(1) + m.group(2) + m.group(1))
        mode = json.loads(m.group(3) + m.group(4) + m.group(3))
        out.append((q, mode))
    return out


def load_html_examples() -> list[tuple[str, str]]:
    """Legacy compatibility: static index guide examples were removed in Phase 2."""
    return []


def manifest_html_diff() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    manifest = set(load_manifest_examples())
    return manifest, set()
