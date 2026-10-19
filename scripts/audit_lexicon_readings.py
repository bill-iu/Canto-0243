"""Read-only pronunciation audit; unlisted word readings require contextual review."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.han import is_han_char  # noqa: E402
from app.utils.jyutping_codec import get_0243_code  # noqa: E402

FIELDS = ("char", "jyutping", "code", "expected_code", "source_flags", "issues", "unlisted_syllables", "verdict")


def audit_rows(rows: list[tuple], readings: dict[str, set[str]]) -> tuple[list[dict], dict]:
    findings = []
    counts: Counter = Counter()
    for literal, jyutping, code, flags in rows:
        counts["scanned_rows"] += 1
        # Mixed literals intentionally store letter wildcards / literal digits.
        if not literal or not all(is_han_char(char) for char in literal):
            counts["non_han_or_mixed_rows"] += 1
            continue
        counts["han_rows"] += 1
        syllables = jyutping.split()
        issues = []
        expected = get_0243_code(jyutping)
        if code != expected:
            issues.append("code_mismatch")
        if len(syllables) != len(literal):
            issues.append("syllable_count")
        unlisted = []
        if len(literal) > 1 and len(syllables) == len(literal):
            counts["han_word_rows"] += 1
            unlisted = [
                f"{char}:{syllable}"
                for char, syllable in zip(literal, syllables)
                if char in readings and syllable not in readings[char]
            ]
            if unlisted:
                issues.append("unlisted_word_syllable")
        if issues:
            counts.update(issues)
            findings.append(dict(zip(FIELDS, (
                literal, jyutping, code, expected, flags, ";".join(issues),
                " ".join(unlisted), "pending",
            ))))
    counts["pending_rows"] = len(findings)
    return sorted(findings, key=lambda row: (row["char"], row["jyutping"])), dict(counts)


def scan_database(db_path: Path, char_path: Path) -> tuple[list[dict], dict]:
    readings: dict[str, set[str]] = defaultdict(set)
    with char_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"char", "jyutping"}.issubset(reader.fieldnames or []):
            raise ValueError("character reference requires char and jyutping columns")
        for row in reader:
            if row["char"] and row["jyutping"]:
                readings[row["char"]].add(row["jyutping"])
    if not readings:
        raise ValueError("character reading reference is empty")
    with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT char, jyutping, code, source_flags FROM words").fetchall()
    findings, summary = audit_rows(rows, readings)
    summary.update({
        "db_path": str(db_path.resolve()),
        "db_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest(),
        "char_reference_sha256": hashlib.sha256(char_path.read_bytes()).hexdigest(),
        "policy": "report_only; unlisted syllables include legitimate word-level tone changes",
    })
    return findings, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "lyrics.db")
    parser.add_argument("--char-reference", type=Path, default=ROOT / "data/rime/char.csv")
    parser.add_argument("--output-dir", type=Path, help="Create a new directory with findings.tsv and summary.json")
    args = parser.parse_args(argv)
    try:
        findings, summary = scan_database(args.db, args.char_reference)
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            with (args.output_dir / "findings.tsv").open("x", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(findings)
            (args.output_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
            )
        print(json.dumps(summary, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Cannot audit lexicon readings: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
