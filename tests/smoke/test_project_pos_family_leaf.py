"""語彙族葉提案／審核 fail-closed smoke."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.project_pos import parse_project_pos_tsv  # noqa: E402
from ingest.project_pos_family_leaf import (  # noqa: E402
    HEADER,
    FamilyLeafError,
    apply_review,
    freeze_mother_body,
    propose_chengyu,
)


def write_tsv(path: Path, body: str) -> None:
    path.write_text("literal\tpos\tfamily\tvoice\tnote\n" + body, encoding="utf-8")


def test_propose_intersection_and_source_meta() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tsv, mother = root / "pos.tsv", root / "mother.txt"
        write_tsv(tsv, "畫蛇添足\tv\tidiom\t\tseed\n普通詞\tn\t\t\tseed\n")
        freeze_mother_body(mother, tsv=tsv)
        source = root / "idiom.csv"
        source.write_text("word,pinyin\n画蛇添足,x\n画蛇添足,x\n普通词,x\n詞庫外,x\n", encoding="utf-8")
        proposals, meta = root / "proposals.tsv", root / "meta.json"
        result = propose_chengyu(
            source,
            source_commit="abc123",
            mother_path=mother,
            out_path=proposals,
            meta_path=meta,
            lexicon_literals={"畫蛇添足", "普通詞"},
        )
        with proposals.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        assert [row["literal"] for row in rows] == ["畫蛇添足"]
        assert rows[0]["proposed_family"] == "chengyu" and rows[0]["verdict"] == "pending"
        assert result["source_commit"] == "abc123" and len(result["source_sha256"]) == 64
        assert json.loads(meta.read_text(encoding="utf-8"))["matched"] == 1


def test_apply_review_only_changes_family_and_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tsv, mother, review = root / "pos.tsv", root / "mother.txt", root / "review.tsv"
        write_tsv(tsv, "畫蛇添足\tv\tidiom\tactive\tseed\n留傘\tn\tidiom\t\tseed\n")
        freeze_mother_body(mother, tsv=tsv)
        with review.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow({"literal": "畫蛇添足", "current_family": "idiom", "proposed_family": "chengyu", "source": "china-idiom", "evidence": "membership", "confidence": "medium", "verdict": "accept", "review_note": "ok"})
            writer.writerow({"literal": "留傘", "current_family": "idiom", "proposed_family": "chengyu", "source": "agent", "evidence": "ambiguous", "confidence": "high", "verdict": "keep_idiom", "review_note": "cross-boundary"})
        first = apply_review(review, mother_path=mother, tsv=tsv)
        table = parse_project_pos_tsv(tsv)
        assert first["changed"] == 1 and table["畫蛇添足"].family == "chengyu"
        assert table["畫蛇添足"].pos == frozenset({"v"}) and table["畫蛇添足"].voice == "active"
        assert table["留傘"].family == "idiom"
        assert apply_review(review, mother_path=mother, tsv=tsv)["changed"] == 0


def test_bad_review_fails_before_write() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tsv, mother, review = root / "pos.tsv", root / "mother.txt", root / "review.tsv"
        write_tsv(tsv, "甲\tn\tidiom\t\tseed\n")
        freeze_mother_body(mother, tsv=tsv)
        before = tsv.read_bytes()
        review.write_text("\t".join(HEADER) + "\n甲\tidiom\tbad\tagent\tx\thigh\taccept\t\n", encoding="utf-8")
        try:
            apply_review(review, mother_path=mother, tsv=tsv)
            raise AssertionError("expected FamilyLeafError")
        except FamilyLeafError:
            pass
        assert tsv.read_bytes() == before


def main() -> None:
    test_propose_intersection_and_source_meta()
    test_apply_review_only_changes_family_and_is_idempotent()
    test_bad_review_fails_before_write()
    print("test_project_pos_family_leaf: ok")


if __name__ == "__main__":
    main()
