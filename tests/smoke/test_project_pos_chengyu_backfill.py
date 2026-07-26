"""China-idiom 成語 POS 補標 fail-closed smoke."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.project_pos_chengyu_backfill import (  # noqa: E402
    ChengyuPosError,
    POS_REVIEW_HEADER,
    apply_pos_review,
    build_pos_review,
    classify_record,
    load_backfill_scope,
    verify_source,
    write_pos_quality,
)


FAMILY_HEADER = (
    "literal", "scope", "current_family", "proposed_family", "source",
    "evidence", "confidence", "verdict", "review_note",
)


def _write_family_review(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FAMILY_HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow({"literal": "畫蛇添足", "scope": "lexicon-pos-gap", "proposed_family": "chengyu", "verdict": "accept"})
        writer.writerow({"literal": "留在母體", "scope": "mother-external-match", "proposed_family": "chengyu", "verdict": "accept"})
        writer.writerow({"literal": "已拒絕", "scope": "lexicon-pos-gap", "proposed_family": "chengyu", "verdict": "reject"})


def test_scope_and_source_are_pinned() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        family_review = root / "family.tsv"
        _write_family_review(family_review)
        assert load_backfill_scope(family_review, expected_count=1) == ["畫蛇添足"]

        source = root / "idiom.csv"
        source.write_text("word,pinyin,explanation,derivation,example\n畫蛇添足,x,x,x,x\n", encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        meta = root / "source.json"
        meta.write_text(json.dumps({"source_commit": "abc", "source_sha256": digest}), encoding="utf-8")
        verify_source(source, source_commit="abc", source_meta_path=meta)
        try:
            verify_source(source, source_commit="wrong", source_meta_path=meta)
            raise AssertionError("expected source mismatch")
        except ChengyuPosError:
            pass


def test_clear_worked_examples_classify_conservatively() -> None:
    noun = classify_record("一字之師", "改正一個字的老師。", "他可稱為～。")
    assert noun.pos == ("n",) and noun.voice == ""

    verb = classify_record("一刀兩斷", "比喻堅決斷絕關係。", "他們終於～了。")
    assert verb.pos == ("v",) and verb.voice == ""

    adjective = classify_record("一乾二淨", "形容十分徹底，一點兒也不剩。", "早忘得～。")
    assert adjective.pos == ("a",)

    adverb = classify_record("不約而同", "事先沒有約定而相互一致。", "大家～地回答。")
    assert adverb.pos == ("r",)

    multi = classify_record("一清二楚", "十分清楚、明白。", "看得～，又～地說明。")
    assert multi.pos == ("a", "r")

    formula = classify_record("阿彌陀佛", "佛教語，用作口頭誦頌的佛號，表示祈禱或感謝。", "和尚念經，～。")
    assert formula.pos == ("x",)

    passive = classify_record("任人宰割", "比喻不能掌握命運，任由別人處置。", "只能～。")
    assert passive.pos == ("v",) and passive.voice == "passive"

    not_passive = classify_record("身不由己", "指行為不能由自己作主。", "人在江湖，～。")
    assert not_passive.voice == ""
    assert classify_record("人不知鬼不覺", "形容事情秘密，沒有被人發覺。", "無").voice == ""
    assert classify_record("病國殃民", "使國家受害，人民遭受苦難。", "無").voice == ""

    unknown = classify_record("一個巴掌拍不響", "比喻事情不會由單方面引起。", "無")
    assert unknown.pos == ("u",) and unknown.confidence == "low"

    referent = classify_record("瞞天大謊", "指天大的謊話。形容漫無邊際的假話。", "這是～。")
    assert referent.pos == ("n",)

    action = classify_record("報仇雪恥", "指報復冤仇，洗刷恥辱。", "無")
    assert action.pos == ("v",)

    state_and_manner = classify_record("戀戀不捨", "形容非常留戀，捨不得離開。", "他～地離去。")
    assert state_and_manner.pos == ("a", "r")

    assert classify_record("三朋四友", "泛指各種朋友。", "交得～。" ).pos == ("n",)
    assert classify_record("作繭自縛", "比喻自己使自己受困。", "弄得～。" ).pos == ("v",)
    assert classify_record("狐群狗黨", "比喻勾結在一起的壞人。", "無").pos == ("n",)
    assert classify_record("知命之年", "知道自己命運的年齡。指五十歲。", "無").pos == ("n",)
    assert classify_record("走南闖北", "指走過很多地方，也泛指闖蕩。", "無").pos == ("v",)


def test_complete_source_writes_terminal_review_ledger() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        family_review = root / "family.tsv"
        with family_review.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FAMILY_HEADER, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for literal in ("一字之師", "一個巴掌拍不響"):
                writer.writerow({"literal": literal, "scope": "lexicon-pos-gap", "proposed_family": "chengyu", "verdict": "accept"})
        source = root / "idiom.csv"
        source.write_text(
            "word,pinyin,explanation,derivation,example\n"
            "一字之師,y,改正一個字的老師。,d,他可稱為～。\n"
            "一個巴掌拍不響,y,比喻事情不會由單方面引起。,d,無\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        meta = root / "source.json"
        meta.write_text(json.dumps({"source_commit": "abc", "source_sha256": digest}), encoding="utf-8")
        review = root / "pos-review.tsv"
        result = build_pos_review(
            source,
            source_commit="abc",
            family_review_path=family_review,
            source_meta_path=meta,
            out_path=review,
            expected_count=2,
        )
        with review.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            assert tuple(reader.fieldnames or ()) == POS_REVIEW_HEADER
            rows = {row["literal"]: row for row in reader}
        assert result["reviewed"] == 2 and result["pending"] == 0
        assert rows["一字之師"]["pos"] == "n"
        assert rows["一個巴掌拍不響"]["pos"] == "u"
        assert all(row["family"] == "chengyu" and row["verdict"] == "accept" for row in rows.values())


def _write_pos_review(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=POS_REVIEW_HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow({"literal": "一字之師", "pos": "n", "family": "chengyu", "source": "china-idiom+agent", "evidence": "nominal-slot", "confidence": "high", "verdict": "accept", "review_note": "reviewed"})
        writer.writerow({"literal": "一個巴掌拍不響", "pos": "u", "family": "chengyu", "source": "china-idiom+agent", "evidence": "insufficient", "confidence": "low", "verdict": "accept", "review_note": "reviewed"})


def test_apply_requires_fresh_quality_and_is_conflict_safe() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        family_review, review = root / "family.tsv", root / "pos-review.tsv"
        with family_review.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FAMILY_HEADER, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for literal in ("一字之師", "一個巴掌拍不響"):
                writer.writerow({"literal": literal, "scope": "lexicon-pos-gap", "proposed_family": "chengyu", "verdict": "accept"})
        _write_pos_review(review)
        quality = root / "quality.json"
        quality_result = write_pos_quality(
            review,
            family_review_path=family_review,
            out_path=root / "quality.tsv",
            meta_path=quality,
            report_path=root / "quality.md",
            expected_count=2,
            min_sample=1,
        )
        assert quality_result["sample_n"] == 2
        assert quality_result["review_sha256"] == hashlib.sha256(review.read_bytes()).hexdigest()
        assert quality_result["pass"] is True
        tsv = root / "project-pos.tsv"
        tsv.write_text("literal\tpos\tfamily\tvoice\tnote\n既有\tv\t\t\treview\n", encoding="utf-8")
        first = apply_pos_review(
            review,
            family_review_path=family_review,
            quality_meta_path=quality,
            tsv=tsv,
            expected_count=2,
            min_sample=1,
        )
        assert first["added"] == 2 and first["changed"] == 2
        assert apply_pos_review(
            review,
            family_review_path=family_review,
            quality_meta_path=quality,
            tsv=tsv,
            expected_count=2,
            min_sample=1,
        )["changed"] == 0

        text = tsv.read_text(encoding="utf-8").replace("一字之師\tn\tchengyu", "一字之師\tv\tchengyu")
        tsv.write_text(text, encoding="utf-8")
        before = tsv.read_bytes()
        try:
            apply_pos_review(
                review,
                family_review_path=family_review,
                quality_meta_path=quality,
                tsv=tsv,
                expected_count=2,
                min_sample=1,
            )
            raise AssertionError("expected existing-row conflict")
        except ChengyuPosError:
            pass
        assert tsv.read_bytes() == before


def main() -> None:
    test_scope_and_source_are_pinned()
    test_clear_worked_examples_classify_conservatively()
    test_complete_source_writes_terminal_review_ledger()
    test_apply_requires_fresh_quality_and_is_conflict_safe()
    print("test_project_pos_chengyu_backfill: ok")


if __name__ == "__main__":
    main()
