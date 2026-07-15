"""詞庫版本標籤（與 PWA VITE_LEXICON_VERSION / release tag 對齊）。"""
from __future__ import annotations

import os
import re
from pathlib import Path

_FALLBACK = "v1.0.9"
_README = Path("README.md")


def lexicon_version() -> str:
    env = (os.getenv("LEXICON_VERSION") or os.getenv("VITE_LEXICON_VERSION") or "").strip()
    if env:
        return env if env.startswith("v") or env == "dev" else f"v{env}"
    if _README.is_file():
        text = _README.read_text(encoding="utf-8")
        m = re.search(r"目前版本：\*\*(v[\w.-]+)\*\*", text)
        if m:
            return m.group(1)
    return _FALLBACK
