"""搜尋教學範例 — `frontend/guide-i18n.mjs` manifest 為準（CONTEXT § 搜尋教學驗收）。"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "frontend" / "guide-i18n.mjs"
INDEX_PATH = REPO_ROOT / "frontend" / "index.html"

MANIFEST_EXAMPLE_RE = re.compile(
    r"\{\s*query:\s*'((?:\\'|[^'])*)',\s*mode:\s*'([^']+)'\s*\}"
)
HTML_EXAMPLE_RE = re.compile(r'data-query="([^"]+)"\s+data-mode="([^"]+)"')


def load_manifest_examples() -> list[tuple[str, str]]:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    return [(m.group(1), m.group(2)) for m in MANIFEST_EXAMPLE_RE.finditer(text)]


def load_html_examples() -> list[tuple[str, str]]:
    text = INDEX_PATH.read_text(encoding="utf-8")
    return HTML_EXAMPLE_RE.findall(text)


def manifest_html_diff() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    manifest = set(load_manifest_examples())
    html = set(load_html_examples())
    return manifest - html, html - manifest