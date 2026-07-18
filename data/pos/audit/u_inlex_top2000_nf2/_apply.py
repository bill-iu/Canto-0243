"""Apply top2000_nf agent labels + G1 sample (note u-inlex-nf2k)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

from ingest.project_pos import DEFAULT_META, load_meta, parse_project_pos_tsv, write_carrier
from ingest.project_pos_audit import upsert_ssot_rows

ROOT = Path(__file__).resolve().parents[4]
DIR = Path(__file__).resolve().parent
ALLOWED = set("nvarx")
NOTE_MARK = "u-inlex-nf2b"


def _norm_pos(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw or raw == "u":
        return None
    tags = [t.strip() for t in raw.split(",") if t.strip()]
    if not tags or any(t not in ALLOWED for t in tags) or "u" in tags:
        return None
    return ",".join(sorted(set(tags)))


def load_fixes() -> tuple[list[dict], list[dict]]:
    fixes, keep_u = [], []
    seen: set[str] = set()
    for p in sorted(DIR.glob("label_part*.tsv")):
        with p.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                lit = (r.get("literal") or "").strip()
                if not lit or lit in seen:
                    continue
                seen.add(lit)
                pos = _norm_pos(r.get("pos") or "")
                if not pos:
                    keep_u.append({"literal": lit, "pos": (r.get("pos") or "u").strip() or "u", "note": r.get("note") or ""})
                    continue
                fam = (r.get("family") or "").strip()
                if fam not in ("", "idiom"):
                    fam = ""
                fixes.append(
                    {
                        "literal": lit,
                        "fix_pos": pos,
                        "fix_family": fam,
                        "fix_voice": "",
                        "note": (r.get("note") or "").strip(),
                        "audit_note": "agent-label",
                    }
                )
    return fixes, keep_u


def apply_labels(*, dry_run: bool = False) -> dict:
    fixes, keep_u = load_fixes()
    table = parse_project_pos_tsv()
    usable = []
    skipped = Counter()
    for f in fixes:
        row = table.get(f["literal"])
        if not row:
            skipped["missing"] += 1
            continue
        if row.pos != frozenset({"u"}):
            skipped["already_formal"] += 1
            continue
        usable.append(f)
    before_u = sum(1 for r in table.values() if r.pos == frozenset({"u"}))
    if dry_run:
        return {"dry_run": True, "usable": len(usable), "keep_u": len(keep_u), "skipped": dict(skipped), "before_u": before_u}
    up = upsert_ssot_rows(usable, note_suffix=NOTE_MARK)
    write_carrier()
    after = parse_project_pos_tsv()
    after_u = sum(1 for r in after.values() if r.pos == frozenset({"u"}))
    result = {
        "usable": len(usable),
        "keep_u": len(keep_u),
        "upsert": up,
        "skipped": dict(skipped),
        "before_u": before_u,
        "after_u": after_u,
    }
    meta = load_meta()
    meta["u_inlex_nf2k"] = result
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def sample_gate(*, seed: int = 44, round_id: int = 1) -> dict:
    table = parse_project_pos_tsv()
    universe = [
        lit for lit, r in table.items() if NOTE_MARK in (r.note or "") and r.pos != frozenset({"u"})
    ]
    n = min(len(universe), max(50, math.ceil(len(universe) * 0.05))) if universe else 0
    rng = random.Random(seed)
    sample = sorted(rng.sample(universe, n)) if n and n < len(universe) else sorted(universe)
    out = DIR / f"nf2k_gate_r{round_id}.tsv"
    header = ["literal", "pos", "family", "voice", "note", "trust", "verdict", "fix_pos", "audit_note"]
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for lit in sample:
            r = table[lit]
            w.writerow(
                {
                    "literal": lit,
                    "pos": ",".join(sorted(r.pos)),
                    "family": r.family,
                    "voice": r.voice,
                    "note": r.note,
                    "trust": r.trust(),
                    "verdict": "",
                    "fix_pos": "",
                    "audit_note": "",
                }
            )
    meta = {"round": round_id, "seed": seed, "universe": len(universe), "sample_n": n, "out": str(out.relative_to(ROOT)).replace("\\", "/")}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "apply", "sample", "run"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "status":
        fixes, keep_u = load_fixes()
        pos = Counter((f["fix_pos"] for f in fixes))
        print(json.dumps({"formal": len(fixes), "keep_u": len(keep_u), "pos_top": pos.most_common(10)}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "apply":
        print(json.dumps(apply_labels(dry_run=args.dry_run), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "sample":
        print(json.dumps(sample_gate(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "run":
        print(json.dumps(apply_labels(dry_run=False), ensure_ascii=False, indent=2))
        print(json.dumps(sample_gate(), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
