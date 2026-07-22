"""詞庫版本標籤（與 PWA VITE_LEXICON_VERSION / release tag 對齊）。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from app.payload_root import get_payload_root

_FALLBACK = "v1.0.9"


def lexicon_version() -> str:
    env = (os.getenv("LEXICON_VERSION") or os.getenv("VITE_LEXICON_VERSION") or "").strip()
    if env:
        return env if env.startswith("v") or env == "dev" else f"v{env}"

    roots: list[Path] = []
    try:
        roots.append(get_payload_root())
    except Exception:
        pass
    roots.append(Path.cwd())
    # de-dupe
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        manifest = root / "portable-manifest.json"
        if manifest.is_file():
            try:
                tag = str(json.loads(manifest.read_text(encoding="utf-8")).get("tag") or "")
            except (OSError, json.JSONDecodeError, AttributeError):
                tag = ""
            if re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][\w.-]+)?", tag):
                return tag
        readme = root / "README.md"
        if readme.is_file():
            try:
                text = readme.read_text(encoding="utf-8")
            except OSError:
                continue
            m = re.search(r"目前版本：\*\*(v[\w.-]+)\*\*", text)
            if m:
                return m.group(1)
    return _FALLBACK
