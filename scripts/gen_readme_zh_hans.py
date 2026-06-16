#!/usr/bin/env python3
"""Generate docs/README.zh-Hans.md from README.md (t2s + colloquial → written Chinese)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.readme_zh_hans_written import apply_written_rules, find_colloquial_markers

SRC = REPO_ROOT / "README.md"
DST = REPO_ROOT / "docs" / "README.zh-Hans.md"

LANG_BAR = """<p align="center">
  <a href="../README.md">繁體中文</a> · <b>简体中文</b> · <a href="README.en.md">English</a>
</p>"""

RELATED_DOCS = """| [`README.md`](../README.md) | 繁体中文（GitHub 首页） |
| [`README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文书面语） |
| [`README.en.md`](README.en.md) | English documentation |"""

MAINTAINER_COMMENT = "# 若大幅更新 README.md，可重新生成简体书面语版：\n# python scripts/gen_readme_zh_hans.py"


def _opencc_t2s(text: str) -> str:
    try:
        import opencc
    except ImportError as exc:
        raise SystemExit(
            "Missing opencc-python-reimplemented. Run: pip install -r requirements-dev.txt"
        ) from exc
    return opencc.OpenCC("t2s").convert(text)


def _apply_locale_fixes(text: str) -> str:
    text = re.sub(r"<p align=\"center\">.*?</p>", LANG_BAR, text, count=1, flags=re.DOTALL)
    text = text.replace("<!-- words-count:zh-Hant -->", "<!-- words-count:zh-Hans -->")
    text = text.replace("<!-- /words-count:zh-Hant -->", "<!-- /words-count:zh-Hans -->")
    text = text.replace("目前總詞條列數", "目前总词条列数")
    text = text.replace(
        "README.md               # 繁中（GitHub 首頁）",
        "README.md               # 繁中（GitHub 首页）",
    )
    text = text.replace(
        "├── docs/                   # CONTRIBUTING · README.en · README.zh-Hans · release",
        "├── docs/                   # CONTRIBUTING · README.* · release",
    )
    text = re.sub(
        r"\| \[`README\.md`\]\([^)]+\) \| [^\n]+ \|\n"
        r"\| \[`docs/README\.zh-Hans\.md`\]\([^)]+\) \| [^\n]+ \|\n"
        r"\| \[`docs/README\.en\.md`\]\([^)]+\) \| English documentation \|",
        RELATED_DOCS,
        text,
        count=1,
    )
    text = re.sub(
        r"# 若大幅更新 README\.md[^\n]*\n(?:# [^\n]*\n)?",
        f"{MAINTAINER_COMMENT}\n",
        text,
        count=1,
    )
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "CONTEXT.md", "WORKLOG.md", "AGENTS.md"):
        text = text.replace(f"]({name})", f"](../{name})")
    text = text.replace("docs/CONTRIBUTING.md", "CONTRIBUTING.md")
    text = text.replace("docs/release.md", "release.md")
    text = text.replace("docs/adr/", "adr/")
    return text


def generate(source_text: str | None = None) -> str:
    raw = source_text if source_text is not None else SRC.read_text(encoding="utf-8")
    text = _opencc_t2s(raw)
    text = apply_written_rules(text)
    text = _apply_locale_fixes(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/README.zh-Hans.md from README.md (Simplified written Chinese)."
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing docs/README.zh-Hans.md",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if docs/README.zh-Hans.md differs from generated output",
    )
    parser.add_argument(
        "--strict-colloquial",
        action="store_true",
        help="Exit 1 if generated text still contains Cantonese colloquial markers",
    )
    args = parser.parse_args()

    if not SRC.is_file():
        print(f"Source not found: {SRC}", file=sys.stderr)
        return 1

    draft = generate()
    markers = find_colloquial_markers(draft)
    if args.strict_colloquial and markers:
        print(f"Colloquial markers remain: {', '.join(markers)}", file=sys.stderr)
        return 1

    if args.check:
        if not DST.is_file():
            print(f"Target not found: {DST}", file=sys.stderr)
            return 1
        current = DST.read_text(encoding="utf-8")
        if current == draft:
            print("docs/README.zh-Hans.md is up to date.")
            return 0
        print("docs/README.zh-Hans.md is stale. Run: python scripts/gen_readme_zh_hans.py", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.write(draft)
        return 0

    DST.write_text(draft, encoding="utf-8")
    print(f"Wrote {DST}")
    if markers:
        print(f"Note: remaining markers (may be acceptable): {', '.join(markers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
