"""S2: still-u pattern idioms → formal POS + optional family=idiom (ADR-0060)."""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ingest.project_pos import DEFAULT_META, PosRow, load_meta, parse_project_pos_tsv, write_carrier
from tools.campaigns.project_pos_alias import dual_coverage, is_fragment_note
from tools.campaigns.project_pos_cleanup import _rewrite_table
from tools.campaigns.project_pos_p2 import idiom_pattern

AUDIT = ROOT / "data" / "pos" / "audit" / "u_inlex"

# POS defaults (exclude 之字格 — historical bulk false n/v; leave for manual/u_repair)
_PAT_POS: Dict[str, str] = {
    "AABB": "a",
    "ABAB": "a,r",
    "AABC": "a,r",
    "ABAC": "a,v",
    "不X不Y": "a",
    "一X?Y": "a,v",
    "有無對": "a",
    "AxxA": "a,v",
}
_IDIOM_PATS = frozenset(_PAT_POS)


def propose_pattern_u(lit: str) -> Optional[Tuple[str, str, str]]:
    """Return (pos_csv, pattern, family) or None."""
    pat = idiom_pattern(lit)
    if not pat:
        return None
    pos = _PAT_POS.get(pat)
    if not pos:
        return None
    fam = "idiom" if pat in _IDIOM_PATS else ""
    # 之字格: only set family if not ordinary temporal (idiom_pattern already filters some)
    return pos, pat, fam


def collect_still_u_patterns() -> List[dict]:
    table = parse_project_pos_tsv()
    out: List[dict] = []
    for lit, row in table.items():
        if row.pos != frozenset({"u"}):
            continue
        if is_fragment_note(row.note):
            continue
        prop = propose_pattern_u(lit)
        if not prop:
            continue
        pos, pat, fam = prop
        out.append({"literal": lit, "pos": pos, "pattern": pat, "family": fam})
    return out


def apply_patterns(*, dry_run: bool = False) -> dict:
    props = collect_still_u_patterns()
    by_pat: Counter = Counter(p["pattern"] for p in props)
    if dry_run:
        return {"dry_run": True, "would_apply": len(props), "by_pattern": dict(by_pat)}
    table = parse_project_pos_tsv()
    applied = 0
    for p in props:
        lit = p["literal"]
        row = table.get(lit)
        if not row or row.pos != frozenset({"u"}):
            continue
        pos = frozenset(p["pos"].split(","))
        fam = p["family"] if p["family"] in ("", "idiom") else ""
        note = row.note
        bits = [f"u-pattern:{p['pattern']}", "u-pattern-s2", "review"]
        have = {t.strip() for t in note.split(";") if t.strip()}
        for b in bits:
            if b not in have:
                note = f"{note};{b}" if note else b
                have.add(b)
        table[lit] = PosRow(lit, pos, fam or row.family, row.voice, note)
        applied += 1
    _rewrite_table(table)
    write_carrier()
    cov = dual_coverage()
    result = {
        "applied": applied,
        "by_pattern": dict(by_pat),
        "coverage": cov,
    }
    meta = load_meta()
    meta["u_pattern_s2"] = result
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def sample_gate(*, seed: int = 43, round_id: int = 1) -> dict:
    import csv

    table = parse_project_pos_tsv()
    universe = [
        lit
        for lit, r in table.items()
        if "u-pattern-s2" in (r.note or "") and r.pos != frozenset({"u"})
    ]
    n = min(len(universe), max(50, math.ceil(len(universe) * 0.05))) if universe else 0
    rng = random.Random(seed)
    sample = sorted(rng.sample(universe, n)) if n and n < len(universe) else sorted(universe)
    out = AUDIT / f"u_pattern_s2_gate_r{round_id}.tsv"
    AUDIT.mkdir(parents=True, exist_ok=True)
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
    meta = {"round": round_id, "seed": seed, "universe": len(universe), "sample_n": n, "out": str(out)}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_u_pattern")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dry-run")
    sub.add_parser("run")
    sub.add_parser("sample")
    args = p.parse_args(argv)
    if args.cmd == "dry-run":
        print(json.dumps(apply_patterns(dry_run=True), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "run":
        print(json.dumps(apply_patterns(dry_run=False), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "sample":
        print(json.dumps(sample_gate(), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
