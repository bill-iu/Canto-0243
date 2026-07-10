"""搜尋教學 execution manifest — `frontend/guide-i18n.mjs` 是唯一來源。"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "frontend" / "guide-i18n.mjs"
INDEX_PATH = REPO_ROOT / "frontend" / "index.html"

MANIFEST_EXAMPLE_RE = re.compile(
    r"\{\s*query:\s*'((?:\\'|[^'])*)',\s*mode:\s*'([^']+)'\s*\}"
)


def load_manifest_examples() -> list[tuple[str, str]]:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    return [(m.group(1), m.group(2)) for m in MANIFEST_EXAMPLE_RE.finditer(text)]


def load_html_examples() -> list[tuple[str, str]]:
    """Legacy compatibility: static index guide examples were removed in Phase 2."""
    return []


def manifest_html_diff() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    manifest = set(load_manifest_examples())
    return manifest, set()
