"""Build the pinned Unihan Cantonese reading intersection for admitted characters."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.utils.han import is_han_char
from ingest.lexicon_validate import normalize_lexicon_candidate

UNICODE_VERSION = "17.0.0"
ARCHIVE_URL = f"https://www.unicode.org/Public/{UNICODE_VERSION}/ucd/Unihan.zip"
ARCHIVE_SHA256 = "f7a48b2b545acfaa77b2d607ae28747404ce02baefee16396c5d2d7a8ef34b5e"
DEFAULT_ZIP = ROOT / ".tmp" / f"Unihan-{UNICODE_VERSION}.zip"
OUT_JSON = ROOT / "data" / "lexicon" / "unihan_cantonese.json"
OUT_META = ROOT / "data" / "lexicon" / "unihan_cantonese.manifest.json"
JYUTPING_RE = re.compile(r"^[a-z]{1,6}[1-6]$")


def _property_rows(archive: zipfile.ZipFile) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for filename, prop in (
        ("Unihan_Readings.txt", "kCantonese"),
        ("Unihan_DictionaryLikeData.txt", "kCheungBauer"),
    ):
        for line in archive.read(filename).decode("utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            codepoint, field, value = line.split("\t", 2)
            if field != prop:
                continue
            readings = value.split() if prop == "kCantonese" else value.rsplit(";", 1)[-1].split()
            char = chr(int(codepoint[2:], 16))
            rows.extend((char, prop, reading) for reading in readings if JYUTPING_RE.fullmatch(reading))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--db", type=Path, default=ROOT / "lyrics.db")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    blob = args.zip.read_bytes()
    archive_sha = hashlib.sha256(blob).hexdigest()
    if archive_sha != ARCHIVE_SHA256:
        raise SystemExit(f"Unihan archive sha256 mismatch: {archive_sha}")

    connection = sqlite3.connect(args.db)
    try:
        admitted = {
            row[0]
            for row in connection.execute("select distinct char from words where length = 1")
            if is_han_char(row[0])
        }
    finally:
        connection.close()

    by_pair: dict[tuple[str, str], dict[str, object]] = {}
    property_counts = {"kCantonese": 0, "kCheungBauer": 0}
    with zipfile.ZipFile(args.zip) as archive:
        for char, prop, reading in _property_rows(archive):
            if char not in admitted:
                continue
            normalized = normalize_lexicon_candidate(char, reading)
            if not normalized:
                continue
            literal, jyutping, code = normalized
            key = (literal, jyutping)
            row = by_pair.setdefault(
                key,
                {"char": literal, "jyutping": jyutping, "code": code, "sources": []},
            )
            source = f"unihan-{prop.lower()}"
            sources = row["sources"]
            assert isinstance(sources, list)
            if source not in sources:
                sources.append(source)
                property_counts[prop] += 1

    items = [by_pair[key] for key in sorted(by_pair)]
    meta = {
        "source": "Unicode Unihan",
        "unicode_version": UNICODE_VERSION,
        "archive_url": ARCHIVE_URL,
        "archive_sha256": archive_sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "membership_policy": "intersection_with_existing_single_han_literals",
        "membership_db_sha256": hashlib.sha256(args.db.read_bytes()).hexdigest(),
        "n_admitted_single_han": len(admitted),
        "n_reading_rows": len(items),
        "property_provenance_rows": property_counts,
        "properties": ["kCantonese", "kCheungBauer"],
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if args.write:
        OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
