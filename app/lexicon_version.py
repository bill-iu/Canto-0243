"""詞庫版本標籤（與 PWA VITE_LEXICON_VERSION / release tag 對齊）。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_FALLBACK = "v1.0.9"
_README = Path("README.md")
_PORTABLE_MANIFEST = Path("portable-manifest.json")


def lexicon_version() -> str:
    env = (os.getenv("LEXICON_VERSION") or os.getenv("VITE_LEXICON_VERSION") or "").strip()
    if env:
        return env if env.startswith("v") or env == "dev" else f"v{env}"
    if _PORTABLE_MANIFEST.is_file():
        try:
            tag = str(json.loads(_PORTABLE_MANIFEST.read_text(encoding="utf-8")).get("tag") or "")
        except (OSError, json.JSONDecodeError, AttributeError):
            tag = ""
        if re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][\w.-]+)?", tag):
            return tag
    if _README.is_file():
        text = _README.read_text(encoding="utf-8")
        m = re.search(r"目前版本：\*\*(v[\w.-]+)\*\*", text)
        if m:
            return m.group(1)
    return _FALLBACK
