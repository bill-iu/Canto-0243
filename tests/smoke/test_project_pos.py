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
        assert data["p0HardGate"] is False
        assert data["literals"]["走"]["pos"] == ["v"]
        assert data["literals"]["一石二鳥"]["family"] == "idiom"
        assert data["literals"]["被打"]["voice"] == "passive"


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


def main() -> None:
    test_parse_seed_tsv()
    test_same_pos_and_missing()
    test_hard_gate_off_by_default()
    test_build_carrier_roundtrip()
    test_duplicate_literal_fails()
    test_carrier_payload_shape()
    print("test_project_pos: ok")


if __name__ == "__main__":
    main()