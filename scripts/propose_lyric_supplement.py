"""Find review-only gaps in a local Cantopop Humdrum corpus; never change the DB."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.han import is_han_char  # noqa: E402
from app.utils.trad_chinese import to_traditional  # noqa: E402
from scripts.propose_lexicon_supplement import DEFAULT_CURATED, load_known_literals  # noqa: E402

FIELDS = ("char", "song_count", "occurrences", "corpus_readings", "evidence", "verdict", "jyutping", "note")


def read_phrases(path: Path):
    """Retain aligned single-character syllables; rests/phrases/noise form boundaries."""
    phrase = []
    header_seen = False
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.startswith("**"):
            if line != "**kern\t**text\t**jyutping":
                raise ValueError(f"unsupported corpus spines: {path}:{line_no}")
            header_seen = True
        if not line or line.startswith(("!", "*", "=")):
            if any(token in {"*^", "*v", "*x", "*+"} for token in line.split("\t")):
                raise ValueError(f"unsupported spine change: {path}:{line_no}")
            if line.startswith("*-") and phrase:
                yield phrase
                phrase = []
            continue
        if not header_seen:
            raise ValueError(f"missing corpus spines: {path}:{line_no}")
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError(f"unsupported corpus row: {path}:{line_no}")
        kern, text, reading = parts
        if "{" in kern and phrase:
            yield phrase
            phrase = []
        if "r" in kern or (text != "." and (
            len(text) != 1 or not is_han_char(text) or not re.fullmatch(r"[a-z]+[1-6]", reading)
        )):
            if phrase:
                yield phrase
                phrase = []
            continue
        # A null text token sustains the previous syllable; do not duplicate it.
        if text != ".":
            phrase.append((text, reading, line_no))
        if "}" in kern and phrase:
            yield phrase
            phrase = []
    if not header_seen:
        raise ValueError(f"missing corpus spines: {path}")
    if phrase:
        yield phrase


def collect_ngrams(corpus_dir: Path, *, min_length=2, max_length=6):
    if not 2 <= min_length <= max_length:
        raise ValueError("require 2 <= min-length <= max-length")
    files = sorted(corpus_dir.glob("*.krn"))
    if not files:
        raise ValueError("corpus directory contains no .krn files")
    entries = {}
    hashes = {}
    phrase_count = 0
    for path in files:
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for phrase in read_phrases(path):
            phrase_count += 1
            for width in range(min_length, min(max_length, len(phrase)) + 1):
                for start in range(len(phrase) - width + 1):
                    chunk = phrase[start:start + width]
                    literal = to_traditional("".join(item[0] for item in chunk))
                    entry = entries.setdefault(literal, {"songs": set(), "readings": Counter(), "evidence": []})
                    new_song = path.stem not in entry["songs"]
                    entry["songs"].add(path.stem)
                    entry["readings"][" ".join(item[1] for item in chunk)] += 1
                    if new_song and len(entry["evidence"]) < 3:
                        entry["evidence"].append(f"{path.name}#L{chunk[0][2]}-L{chunk[-1][2]}")
    return entries, {"song_count": len(files), "phrase_count": phrase_count, "input_sha256": hashes}


def propose_lyric_gaps(entries, known, *, min_songs=2, limit=500):
    if min_songs < 1 or limit < 1:
        raise ValueError("require min-songs >= 1 and limit >= 1")
    known = {to_traditional(word) for word in known}
    rows = [dict(zip(FIELDS, (
        literal, len(entry["songs"]), sum(entry["readings"].values()),
        json.dumps(dict(sorted(entry["readings"].items())), ensure_ascii=False),
        ";".join(entry["evidence"]), "pending", "", "",
    ))) for literal, entry in entries.items() if literal not in known and len(entry["songs"]) >= min_songs]
    return sorted(rows, key=lambda row: (-row["song_count"], -row["occurrences"], len(row["char"]), row["char"]))[:limit]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", required=True, type=Path, help="Local Humdrum-files directory")
    parser.add_argument("--db", type=Path, default=ROOT / "lyrics.db")
    parser.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    parser.add_argument("--min-length", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=6)
    parser.add_argument("--min-songs", type=int, default=2)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory; existing paths are refused")
    args = parser.parse_args(argv)
    try:
        known = load_known_literals(args.db, args.curated)
        entries, summary = collect_ngrams(args.corpus_dir, min_length=args.min_length, max_length=args.max_length)
        rows = propose_lyric_gaps(entries, known, min_songs=args.min_songs, limit=args.limit)
        summary.update({"db_sha256": hashlib.sha256(args.db.read_bytes()).hexdigest(),
                        "curated_sha256": hashlib.sha256(args.curated.read_bytes()).hexdigest(),
                        "options": {"min_length": args.min_length, "max_length": args.max_length,
                                    "min_songs": args.min_songs, "limit": args.limit},
                        "candidate_count": len(rows), "policy": "report_only; corpus readings are observations, not approved readings"})
        args.output_dir.mkdir(parents=True, exist_ok=False)
        with (args.output_dir / "gaps.tsv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Lyric proposals: {len(rows)}; songs: {summary['song_count']}; output: {args.output_dir}")
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Cannot propose lyric supplement: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
