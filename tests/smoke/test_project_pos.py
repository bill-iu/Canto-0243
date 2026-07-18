"""專案自建詞性 SSOT + 同詞性 + 載體。

Run: python tests/smoke/test_project_pos.py
  or: pytest tests/smoke/test_project_pos.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.project_pos import (  # noqa: E402
    DEFAULT_TSV,
    ProjectPosError,
    build_carrier_payload,
    campaign_pos_hard_reject,
    parse_project_pos_tsv,
    pos_trust,
    same_pos_literals,
    write_carrier,
)


def test_parse_seed_tsv() -> None:
    table = parse_project_pos_tsv(DEFAULT_TSV)
    assert "開心" in table
    assert "a" in table["開心"].formal_pos()
    assert table["一石二鳥"].family == "idiom"
    assert table["被打"].voice == "passive"


def test_same_pos_and_missing() -> None:
    table = parse_project_pos_tsv(DEFAULT_TSV)
    assert same_pos_literals("開心", "快樂", table) is True
    assert same_pos_literals("開心", "走", table) is False
    assert same_pos_literals("開心", "不存在", table) is None


def test_hard_gate_off_by_default() -> None:
    table = parse_project_pos_tsv(DEFAULT_TSV)
    assert campaign_pos_hard_reject("開心", "走", table, p0_hard_gate=False) is False
    assert campaign_pos_hard_reject("開心", "走", table, p0_hard_gate=True) is True
    assert campaign_pos_hard_reject("開心", "不存在", table, p0_hard_gate=True) is False


def test_build_carrier_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "project-pos-index.json"
        write_carrier(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["version"]
        assert "p0HardGate" in data
        assert data["literals"]["走"]["pos"] == ["v"]
        # seed pair may be overwritten by P0 notes; voice key only if still set
        if "被打" in data["literals"]:
            assert "v" in data["literals"]["被打"]["pos"]


def test_duplicate_literal_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.tsv"
        p.write_text(
            "literal\tpos\tfamily\tvoice\tnote\n"
            "甲\tn\t\t\t\n"
            "甲\tv\t\t\t\n",
            encoding="utf-8",
        )
        try:
            parse_project_pos_tsv(p)
            raise AssertionError("expected ProjectPosError")
        except ProjectPosError as e:
            assert "duplicate" in str(e)


def test_carrier_payload_shape() -> None:
    table = parse_project_pos_tsv(DEFAULT_TSV)
    payload = build_carrier_payload(table, {"version": "0.1.0", "p0_hard_gate": False})
    assert set(payload.keys()) == {"version", "p0HardGate", "literals"}


def test_p0_mother_complete() -> None:
    from ingest.project_pos import load_meta
    from ingest.project_pos_p0 import p0_status

    st = p0_status()
    assert st["mother_body"] > 1000
    assert st["p0_complete"] is True
    assert st["missing"] == 0
    meta = load_meta()
    assert meta.get("p0_hard_gate") is True
    assert meta.get("p0", {}).get("complete") is True


def test_p1_essay_top_k_complete() -> None:
    from ingest.project_pos import load_meta
    from ingest.project_pos_p1 import P1_BODY, p1_status

    assert P1_BODY.is_file()
    st = p1_status()
    assert st["k"] == 5000
    assert st["p1_complete"] is True
    assert st["missing"] == 0
    assert st["coverage"] == 1.0
    meta = load_meta()
    assert meta.get("p1", {}).get("complete") is True
    assert meta.get("p1", {}).get("k") == 5000


def test_p1_audit_artifacts() -> None:
    from pathlib import Path

    from ingest.project_pos import load_meta
    from ingest.project_pos_audit import sample_size_for

    assert sample_size_for(0) == 0
    assert sample_size_for(10) == 10
    assert sample_size_for(245) == 50
    assert sample_size_for(2962) == 149
    meta = load_meta()
    assert "p1_audit" in meta
    assert meta["p1_audit"].get("sample_n") == 322
    assert Path("data/pos/audit/p1_audit_report.md").is_file()
    assert Path("data/pos/audit/p1_sample_verdicts.tsv").is_file()


def test_trust_tiers() -> None:
    assert pos_trust("seed") == "high"
    assert pos_trust("audit-high;review") == "high"
    assert pos_trust("numeral;heuristic") == "high"
    assert pos_trust("cow-multi") == "medium"
    assert pos_trust("cow-single") == "low"
    assert pos_trust("no-source;fallback") == "low"

    table = parse_project_pos_tsv(DEFAULT_TSV)
    # Find a cow-single row if present: gate empty, raw formal may exist
    cow_single = next((r for r in table.values() if "cow-single" in r.note), None)
    if cow_single:
        assert cow_single.trust() == "low"
        assert cow_single.gate_pos() == frozenset()
        assert same_pos_literals(cow_single.literal, "走", table) is None

    cow_multi = next((r for r in table.values() if "cow-multi" in r.note and r.formal_pos()), None)
    if cow_multi:
        assert cow_multi.trust() == "medium"
        assert cow_multi.gate_pos() == cow_multi.formal_pos()

    payload = build_carrier_payload(table, {"version": "0.1.0", "p0_hard_gate": True})
    if cow_single:
        ent = payload["literals"][cow_single.literal]
        assert ent.get("trust") == "low"
        assert "gate" not in ent
        assert "show" not in ent


def main() -> None:
    test_parse_seed_tsv()
    test_same_pos_and_missing()
    test_hard_gate_off_by_default()
    test_build_carrier_roundtrip()
    test_duplicate_literal_fails()
    test_carrier_payload_shape()
    test_p0_mother_complete()
    test_p1_essay_top_k_complete()
    test_p1_audit_artifacts()
    test_trust_tiers()
    print("test_project_pos: ok")


if __name__ == "__main__":
    main()