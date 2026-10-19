"""List corpus-backed lexicon gaps for review; never admit words or guess readings."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.han import is_han_char  # noqa: E402
from app.utils.trad_chinese import to_traditional  # noqa: E402

DEFAULT_ESSAY = ROOT / "data/essay/essay-cantonese.txt"
DEFAULT_CURATED = ROOT / "data/lexicon/curated_lexicon.json"
FIELDS = ("char", "source_literal", "essay_frequency", "verdict", "jyutping", "note")


def load_known_literals(db_path: Path, curated_path: Path) -> set[str]:
    # mode=ro also rejects missing paths, rather than creating an empty database.
    with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        known = {to_traditional(row[0]) for row in db.execute("SELECT DISTINCT char FROM words")}
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    if not isinstance(curated, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("char"), str) or not row["char"].strip()
        for row in curated
    ):
        raise ValueError("curated lexicon must be a list of rows with non-empty char values")
    # A working DB can predate the reviewed source; do not propose those words again.
    known.update(to_traditional(row["char"].strip()) for row in curated)
    return known


def propose_gaps(
    essay_path: Path,
    known: set[str],
    *,
    min_length: int = 3,
    max_length: int = 6,
    min_frequency: int = 10,
    limit: int = 500,
) -> list[dict]:
    if not 2 <= min_length <= max_length or min_frequency < 1 or limit < 1:
        raise ValueError("require 2 <= min-length <= max-length, min-frequency >= 1 and limit >= 1")
    known = {to_traditional(word) for word in known}
    candidates: dict[str, tuple[int, str]] = {}
    with essay_path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            parts = line.split()
            if len(parts) != 2 or not parts[1].isascii() or not parts[1].isdigit():
                continue
            source_literal, frequency = parts[0], int(parts[1])
            literal = to_traditional(source_literal)
            if (
                not min_length <= len(literal) <= max_length
                or frequency < min_frequency
                or literal in known
                or not all(is_han_char(char) for char in literal)
            ):
                continue
            previous = candidates.get(literal)
            # Variant spellings may already share counts upstream: keep the highest
            # observed frequency, never invent a summed occurrence count.
            if previous is None or (-frequency, source_literal) < (-previous[0], previous[1]):
                candidates[literal] = (frequency, source_literal)
    ranked = sorted(candidates.items(), key=lambda item: (-item[1][0], item[0]))
    return [
        dict(zip(FIELDS, (literal, source_literal, frequency, "pending", "", "")))
        for literal, (frequency, source_literal) in ranked[:limit]
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "lyrics.db")
    parser.add_argument("--essay", type=Path, default=DEFAULT_ESSAY)
    parser.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    parser.add_argument("--min-length", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=6)
    parser.add_argument("--min-frequency", type=int, default=10)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, help="Create a new TSV; refuses to overwrite any existing file")
    args = parser.parse_args(argv)
    try:
        rows = propose_gaps(
            args.essay,
            load_known_literals(args.db, args.curated),
            min_length=args.min_length,
            max_length=args.max_length,
            min_frequency=args.min_frequency,
            limit=args.limit,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Cannot propose lexicon supplement: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
