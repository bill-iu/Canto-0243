"""Verify or propose a pinned daimaruhk/Cantonese.md lexicon refresh.

The default is read-only verification.  Pass ``--output-dir`` to write proposal
artifacts; promotion into tracked SSOT remains an explicit reviewed step.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import is_valid_term, normalize_literal  # noqa: E402
from app.utils.jyutping_codec import get_0243_code  # noqa: E402
from ingest.lexicon_validate import normalize_lexicon_candidate  # noqa: E402

UPSTREAM_COMMIT = "ef5f1a06c7113b0e04776249725f796d33333584"
ARCHIVE = f"https://codeload.github.com/daimaruhk/Cantonese.md/zip/{UPSTREAM_COMMIT}"
ARCHIVE_SHA256 = "627f5d882230f43056288eb6ed8e36ee208b009f37f89ee6a0bdecdb4907d073"
CONTENT_TYPE_FAMILY = {"idioms": "xiehouyu"}
TRACKED_REVIEW = ROOT / "data" / "pos" / "audit" / "cantonese_md_xiehouyu_review.tsv"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
KV_RE = re.compile(r"^(term|termJyutping|answer|answerJyutping):\s*(.*)$", re.M)


def _load_rows(blob: bytes) -> list[dict[str, str]]:
    zf = zipfile.ZipFile(io.BytesIO(blob))
    rows: list[dict[str, str]] = []
    seen_types: set[str] = set()
    for name in zf.namelist():
        normalized = name.replace("\\", "/")
        marker = "/src/contents/"
        if marker not in normalized or not normalized.endswith(".md"):
            continue
        content_type = normalized.split(marker, 1)[1].split("/", 1)[0]
        seen_types.add(content_type)
        text = zf.read(name).decode("utf-8")
        match = FM_RE.search(text)
        if not match:
            continue
        row = {key: value.strip().strip("\"'") for key, value in KV_RE.findall(match.group(1))}
        if row.get("term"):
            row["contentType"] = content_type
            rows.append(row)
    unknown = seen_types - CONTENT_TYPE_FAMILY.keys()
    if unknown:
        raise ValueError(f"unmapped Cantonese.md content type(s): {sorted(unknown)}")
    return rows


def _corrected_readings(literal: str, jyutping: str) -> tuple[str, ...]:
    if literal == "牛𡁻牡丹":
        return ("ngau4 ziu6 maau5 daan1", "ngau4 zeu6 maau5 daan1")
    return (jyutping,)


def _review_index() -> dict[str, str]:
    with TRACKED_REVIEW.open(encoding="utf-8", newline="") as fh:
        return {row["literal"]: row["answer"] for row in csv.DictReader(fh, delimiter="\t")}


def _review_diff(rows: list[dict[str, str]]) -> dict[str, object]:
    current = _review_index()
    upstream = {row["term"]: row.get("answer", "") for row in rows}
    return {
        "added": sorted(upstream.keys() - current.keys()),
        "deleted": sorted(current.keys() - upstream.keys()),
        "changed_answer": sorted(
            term for term in upstream.keys() & current.keys() if upstream[term] != current[term]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "lyrics.db")
    parser.add_argument("--all", action="store_true", help="propose every valid term/answer reading")
    parser.add_argument("--url", default=ARCHIVE)
    parser.add_argument("--sha256", default=ARCHIVE_SHA256)
    parser.add_argument("--output-dir", type=Path, help="write proposal JSON + manifest here")
    args = parser.parse_args()

    request = urllib.request.Request(args.url, headers={"User-Agent": "Canto-0243-fetch"})
    with urllib.request.urlopen(request, timeout=120) as response:
        blob = response.read()
    actual_sha = hashlib.sha256(blob).hexdigest()
    if args.sha256 and actual_sha.lower() != args.sha256.lower():
        raise SystemExit(f"archive sha256 mismatch: {actual_sha}")
    rows = _load_rows(blob)
    diff = _review_diff(rows)

    have: set[str] = set()
    if not args.all:
        if not args.db.is_file():
            raise SystemExit(f"missing db {args.db}; use --all or pass --db")
        connection = sqlite3.connect(args.db)
        try:
            have = {row[0] for row in connection.execute("select distinct char from words")}
        finally:
            connection.close()

    by_pair: dict[tuple[str, str], dict[str, str]] = {}
    skipped = {"empty": 0, "invalid_term": 0, "in_db": 0, "bad_reading": 0, "dup": 0}
    for row in rows:
        for literal_key, reading_key in (("term", "termJyutping"), ("answer", "answerJyutping")):
            raw_literal = row.get(literal_key, "")
            literal = normalize_literal(raw_literal) or raw_literal.strip()
            reading = row.get(reading_key, "").strip()
            if not literal or not reading:
                skipped["empty"] += 1
                continue
            if not is_valid_term(literal):
                skipped["invalid_term"] += 1
                continue
            if not args.all and literal in have:
                skipped["in_db"] += 1
                continue
            for corrected in _corrected_readings(literal, reading):
                normalized = normalize_lexicon_candidate(literal, corrected)
                if not normalized:
                    skipped["bad_reading"] += 1
                    continue
                char, jyutping, code = normalized
                code = code or get_0243_code(jyutping) or ""
                if not code:
                    skipped["bad_reading"] += 1
                    continue
                key = (char, jyutping)
                if key in by_pair:
                    skipped["dup"] += 1
                    continue
                by_pair[key] = {"char": char, "jyutping": jyutping, "code": code}

    items = [by_pair[key] for key in sorted(by_pair)]
    meta = {
        "source": "https://github.com/daimaruhk/Cantonese.md",
        "license": "CC0-1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "upstream_commit": UPSTREAM_COMMIT,
        "archive_url": args.url,
        "archive_sha256": actual_sha,
        "content_type_mapping": CONTENT_TYPE_FAMILY,
        "unknown_content_type_policy": "fail_closed",
        "n_entries_parsed": len(rows),
        "entries_by_content_type": {
            content_type: sum(row["contentType"] == content_type for row in rows)
            for content_type in CONTENT_TYPE_FAMILY
        },
        "n_lexicon_rows": len(items),
        "review_diff": diff,
        "skipped": skipped,
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "cantonese_md_lexicon.proposal.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (args.output_dir / "cantonese_md.proposal.manifest.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 1 if any(diff.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
