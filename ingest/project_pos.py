"""專案自建詞性：清單 parse、同詞性、詞性載體 build（CONTEXT § 詞性與分類）。"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = ROOT / "data" / "pos" / "project_pos.tsv"
DEFAULT_META = ROOT / "data" / "pos" / "project_pos.meta.json"
DEFAULT_CARRIER_OUT = ROOT / "client" / "public" / "project-pos-index.json"

FORMAL_POS = frozenset({"n", "v", "a", "r", "x"})
ALL_POS = FORMAL_POS | frozenset({"u"})
FAMILY_VALUES = frozenset({"", "idiom"})
VOICE_VALUES = frozenset({"", "active", "passive"})
TSV_HEADER = ("literal", "pos", "family", "voice", "note")

POS_LABEL_ZH = {"n": "名", "v": "動", "a": "形", "r": "副", "x": "虛", "u": "未定"}
FAMILY_LABEL_ZH = {"idiom": "熟語"}
VOICE_LABEL_ZH = {"active": "主動", "passive": "被動"}


class ProjectPosError(ValueError):
    """Fail-closed validation / load error."""


@dataclass(frozen=True, slots=True)
class PosRow:
    literal: str
    pos: frozenset[str]
    family: str  # "" | "idiom"
    voice: str  # "" | "active" | "passive"
    note: str = ""

    def formal_pos(self) -> frozenset[str]:
        return frozenset(p for p in self.pos if p in FORMAL_POS)


def split_pos(raw: str) -> frozenset[str]:
    parts = [p.strip().lower() for p in (raw or "").replace("|", ",").split(",") if p.strip()]
    if not parts:
        raise ProjectPosError("pos empty")
    bad = [p for p in parts if p not in ALL_POS]
    if bad:
        raise ProjectPosError(f"unknown pos {bad}")
    return frozenset(parts)


# back-compat
_split_pos = split_pos


def parse_project_pos_tsv(path: Path = DEFAULT_TSV) -> Dict[str, PosRow]:
    if not path.is_file():
        raise ProjectPosError(f"missing {path}")
    out: Dict[str, PosRow] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not reader.fieldnames or tuple(reader.fieldnames[:5]) != TSV_HEADER:
            raise ProjectPosError(f"bad header {reader.fieldnames!r}, want {TSV_HEADER}")
        for i, row in enumerate(reader, start=2):
            lit = (row.get("literal") or "").strip()
            if not lit:
                raise ProjectPosError(f"L{i}: empty literal")
            if lit in out:
                raise ProjectPosError(f"L{i}: duplicate {lit}")
            family = (row.get("family") or "").strip()
            voice = (row.get("voice") or "").strip()
            if family not in FAMILY_VALUES:
                raise ProjectPosError(f"L{i}: bad family {family!r}")
            if voice not in VOICE_VALUES:
                raise ProjectPosError(f"L{i}: bad voice {voice!r}")
            try:
                pos = _split_pos(row.get("pos") or "")
            except ProjectPosError as e:
                raise ProjectPosError(f"L{i}: {e}") from e
            out[lit] = PosRow(
                literal=lit,
                pos=pos,
                family=family,
                voice=voice,
                note=(row.get("note") or "").strip(),
            )
    return out


def load_meta(path: Path = DEFAULT_META) -> dict:
    if not path.is_file():
        return {"version": "0.0.0", "p0_hard_gate": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProjectPosError("meta not object")
    return data


def formal_pos_of(row: Optional[PosRow]) -> frozenset[str]:
    if row is None:
        return frozenset()
    return row.formal_pos()


def same_pos(a: Optional[PosRow], b: Optional[PosRow]) -> bool | None:
    """True same, False clash, None = 詞性缺標 (do not hard-reject)."""
    fa, fb = formal_pos_of(a), formal_pos_of(b)
    if not fa or not fb:
        return None
    return bool(fa & fb)


def same_pos_literals(
    head: str,
    tail: str,
    table: Mapping[str, PosRow],
) -> bool | None:
    return same_pos(table.get(head), table.get(tail))


def campaign_pos_hard_reject(
    head: str,
    tail: str,
    table: Mapping[str, PosRow],
    *,
    p0_hard_gate: bool,
) -> bool:
    """True only when hard gate on and formal pos disjoint."""
    if not p0_hard_gate:
        return False
    rel = same_pos_literals(head, tail, table)
    return rel is False


def build_carrier_payload(
    table: Mapping[str, PosRow],
    meta: Mapping,
) -> dict:
    literals: Dict[str, dict] = {}
    for lit, row in sorted(table.items()):
        entry: dict = {"pos": sorted(row.pos)}
        if row.family:
            entry["family"] = row.family
        if row.voice:
            entry["voice"] = row.voice
        literals[lit] = entry
    return {
        "version": str(meta.get("version") or "0.0.0"),
        "p0HardGate": bool(meta.get("p0_hard_gate")),
        "literals": literals,
    }


def write_carrier(
    out_path: Path = DEFAULT_CARRIER_OUT,
    *,
    tsv: Path = DEFAULT_TSV,
    meta_path: Path = DEFAULT_META,
) -> Path:
    table = parse_project_pos_tsv(tsv)
    meta = load_meta(meta_path)
    payload = build_carrier_payload(table, meta)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return out_path


def cmd_check(_: argparse.Namespace) -> int:
    table = parse_project_pos_tsv()
    meta = load_meta()
    print(json.dumps({"rows": len(table), "version": meta.get("version"), "p0_hard_gate": meta.get("p0_hard_gate")}, ensure_ascii=False))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    out = write_carrier(Path(args.out) if args.out else DEFAULT_CARRIER_OUT)
    table = parse_project_pos_tsv()
    print(json.dumps({"out": str(out), "literals": len(table)}, ensure_ascii=False))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="parse SSOT")
    b = sub.add_parser("build", help="write project-pos-index.json")
    b.add_argument("--out", default="", help="output path")
    args = p.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "build":
        return cmd_build(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
