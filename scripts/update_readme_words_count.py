#!/usr/bin/env python3
"""Sync README word-entry totals from lyrics.db (words table row count)."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "lyrics.db"

README_ZH = REPO_ROOT / "README.md"
README_EN = REPO_ROOT / "README.en.md"

ZH_BEGIN = "<!-- words-count:zh-Hant -->"
ZH_END = "<!-- /words-count:zh-Hant -->"
EN_BEGIN = "<!-- words-count:en -->"
EN_END = "<!-- /words-count:en -->"

ZH_HEADING = "## 最新版本"
EN_HEADING = "## Latest release"


def count_words(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM words").fetchone()[0])
    finally:
        conn.close()


def _format_block(begin: str, end: str, body: str) -> str:
    return f"{begin}\n{body}\n{end}"


def _zh_body(count: int) -> str:
    return f"目前總詞條列數：**{count:,}**（`lyrics.db` · `words` 表）"


def _en_body(count: int) -> str:
    return f"Current word entries: **{count:,}** (`lyrics.db` · `words` table)"


def _replace_or_insert(
    text: str,
    *,
    begin: str,
    end: str,
    body: str,
    heading: str,
) -> str:
    block = _format_block(begin, end, body)
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)

    anchor = f"{heading}\n\n"
    if anchor not in text:
        raise ValueError(f"heading not found for insert: {heading!r}")
    return text.replace(anchor, f"{heading}\n\n{block}\n\n", 1)


def update_readme_files(
    count: int,
    *,
    readme_zh: Path = README_ZH,
    readme_en: Path = README_EN,
) -> list[Path]:
    updated: list[Path] = []

    zh_text = readme_zh.read_text(encoding="utf-8")
    new_zh = _replace_or_insert(
        zh_text,
        begin=ZH_BEGIN,
        end=ZH_END,
        body=_zh_body(count),
        heading=ZH_HEADING,
    )
    if new_zh != zh_text:
        readme_zh.write_text(new_zh, encoding="utf-8")
        updated.append(readme_zh)

    en_text = readme_en.read_text(encoding="utf-8")
    new_en = _replace_or_insert(
        en_text,
        begin=EN_BEGIN,
        end=EN_END,
        body=_en_body(count),
        heading=EN_HEADING,
    )
    if new_en != en_text:
        readme_en.write_text(new_en, encoding="utf-8")
        updated.append(readme_en)

    return updated


def readme_counts_match(db_path: Path = DEFAULT_DB) -> bool:
    count = count_words(db_path)
    zh = README_ZH.read_text(encoding="utf-8")
    en = README_EN.read_text(encoding="utf-8")
    return _zh_body(count) in zh and _en_body(count) in en


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update README.md / README.en.md with lyrics.db words row count."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if README totals differ from the database",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    count = count_words(db_path)
    if args.check:
        if readme_counts_match(db_path):
            print(f"README word count OK: {count:,}")
            return 0
        print(f"README word count stale (db has {count:,})", file=sys.stderr)
        return 1

    updated = update_readme_files(count)
    if updated:
        names = ", ".join(p.name for p in updated)
        print(f"Updated {names} -> {count:,} word entries")
    else:
        print(f"No README changes (already {count:,} word entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
