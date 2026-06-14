#!/usr/bin/env python3
"""Deprecated helper: OpenCC t2s draft from README.md.

README.zh-Hans.md is maintained as Simplified **written Chinese** (书面语).
Do not overwrite README.zh-Hans.md in release workflow; use --stdout to preview.
"""

from __future__ import annotations

import argparse
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
| [`README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文书面语） |
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
        "README.md · README.en.md · LICENSE",
        "README.md · README.zh-Hans.md · README.en.md · LICENSE",
    )
    text = re.sub(
        r"\| \[`README\.md`\]\(README\.md\) \| [^\n]+ \|\n"
        r"(?:\| \[`README\.zh-Hans\.md`\]\(README\.zh-Hans\.md\) \| [^\n]+ \|\n)?"
        r"\| \[`README\.en\.md`\]\(README\.en\.md\) \| English documentation \|",
        RELATED_DOCS,
        text,
        count=1,
    )
    text = text.replace("**授權**：程式碼依", "**授权**：程序代码依")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print draft to stdout instead of overwriting README.zh-Hans.md",
    )
    args = parser.parse_args()
    if not SRC.is_file():
        print(f"Source not found: {SRC}", file=sys.stderr)
        return 1
    draft = generate()
    if args.stdout:
        sys.stdout.write(draft)
        return 0
    print(
        "Refusing to overwrite README.zh-Hans.md (maintained as written Chinese). "
        "Use --stdout to preview an OpenCC draft.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
