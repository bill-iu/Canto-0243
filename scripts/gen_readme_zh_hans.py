#!/usr/bin/env python3
"""Regenerate README.zh-Hans.md from README.md (OpenCC t2s + locale fixes)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "README.md"
DST = REPO_ROOT / "README.zh-Hans.md"

LANG_BAR = """<p align="center">
  <a href="README.md">繁體中文</a> · <b>简体中文</b> · <a href="README.en.md">English</a>
</p>"""

RELATED_DOCS = """| [`README.md`](README.md) | 繁体中文（GitHub 首页） |
| [`README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文） |
| [`README.en.md`](README.en.md) | English documentation |"""


def generate() -> str:
    try:
        import opencc
    except ImportError as exc:
        raise SystemExit(
            "Missing opencc-python-reimplemented. Run: pip install -r requirements-dev.txt"
        ) from exc

    text = opencc.OpenCC("t2s").convert(SRC.read_text(encoding="utf-8"))
    text = re.sub(r"<p align=\"center\">.*?</p>", LANG_BAR, text, count=1, flags=re.DOTALL)
    text = text.replace("<!-- words-count:zh-Hant -->", "<!-- words-count:zh-Hans -->")
    text = text.replace("<!-- /words-count:zh-Hant -->", "<!-- /words-count:zh-Hans -->")
    text = text.replace(
        "README.md · README.zh-Hans.md · README.en.md · LICENSE",
        "README.md · README.zh-Hans.md · README.en.md · LICENSE",
    )
    text = text.replace(
        "README.md · README.en.md · LICENSE",
        "README.md · README.zh-Hans.md · README.en.md · LICENSE",
    )
    text = re.sub(
        r"\| \[`README\.md`\]\(README\.md\) \| [^\n]+ \|\n"
        r"\| \[`README\.zh-Hans\.md`\]\(README\.zh-Hans\.md\) \| [^\n]+ \|\n"
        r"\| \[`README\.en\.md`\]\(README\.en\.md\) \| English documentation \|",
        RELATED_DOCS,
        text,
        count=1,
    )
    text = re.sub(
        r"\| \[`README\.md`\]\(README\.md\) \| [^\n]+ \|\n"
        r"\| \[`README\.en\.md`\]\(README\.en\.md\) \| English documentation \|",
        RELATED_DOCS,
        text,
        count=1,
    )
    text = text.replace(
        "**授权**：程式码依",
        "**授权**：程序代码依",
    )
    return text


def main() -> int:
    if not SRC.is_file():
        print(f"Source not found: {SRC}", file=sys.stderr)
        return 1
    DST.write_text(generate(), encoding="utf-8")
    print(f"Wrote {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
