"""Apply the reviewed Cantonese.md xiehouyu rows to the project POS SSOT."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data" / "pos" / "audit" / "cantonese_md_xiehouyu_review.tsv"
PROJECT_POS = ROOT / "data" / "pos" / "project_pos.tsv"
PROJECT_HEADER = ("literal", "pos", "family", "voice", "note")
REVIEW_HEADER = ("literal", "answer", "pos", "family", "source", "evidence")


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def main() -> int:
    project_header, project_rows = _read(PROJECT_POS)
    review_header, review_rows = _read(REVIEW)
    if tuple(project_header[:5]) != PROJECT_HEADER:
        raise SystemExit(f"bad project POS header: {project_header!r}")
    if tuple(review_header) != REVIEW_HEADER:
        raise SystemExit(f"bad review header: {review_header!r}")
    if len(review_rows) != 241 or len({row["literal"] for row in review_rows}) != 241:
        raise SystemExit("review must contain exactly 241 unique terms")
    if {row["family"] for row in review_rows} != {"xiehouyu"}:
        raise SystemExit("review family must be xiehouyu")

    by_literal = {row["literal"]: row for row in project_rows}
    for row in review_rows:
        literal = row["literal"]
        current = by_literal.get(literal, {key: "" for key in PROJECT_HEADER})
        current.update(
            literal=literal,
            pos=row["pos"],
            family="xiehouyu",
            note="cantonese-md-xiehouyu;answer-function;review",
        )
        by_literal[literal] = current

    with PROJECT_POS.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=project_header,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(by_literal[key] for key in sorted(by_literal))
    print(f"synced {len(review_rows)} reviewed xiehouyu rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
