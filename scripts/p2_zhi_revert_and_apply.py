"""Revert bulk zhi-n-fix; re-apply only audited P2 gate BAD fixes."""
from __future__ import annotations

import csv
from pathlib import Path

from ingest.project_pos import PosRow, parse_project_pos_tsv, write_carrier
from ingest.project_pos_audit import upsert_ssot_rows
from ingest.project_pos_cleanup import _rewrite_table

BASE = Path("data/pos/audit/full_r1/gate_reconfirm")


def main() -> None:
    t = parse_project_pos_tsv()
    rev = 0
    for lit, r in list(t.items()):
        if "zhi-n-fix" not in r.note.split(";"):
            continue
        if r.pos != frozenset({"v"}):
            continue
        bits = [b for b in r.note.split(";") if b and b not in ("zhi-n-fix", "zhi-n-restore")]
        note = ";".join(bits + ["zhi-n-revert"])
        t[lit] = PosRow(
            literal=lit,
            pos=frozenset({"n"}),
            family=r.family,
            voice=r.voice,
            note=note,
        )
        rev += 1
    _rewrite_table(t)
    print("reverted bulk v->n", rev)

    fixes = []
    for p in sorted(BASE.glob("p2_gate_sample*.tsv")):
        for r in csv.DictReader(p.open(encoding="utf-8"), delimiter="\t"):
            v = (r.get("verdict") or "").upper()
            if v not in ("BAD", "FIX"):
                continue
            fp = (r.get("fix_pos") or "").strip()
            if not fp:
                continue
            fam = (r.get("fix_family") or r.get("family") or "idiom").strip() or "idiom"
            fixes.append(
                {
                    "literal": r["literal"].strip(),
                    "fix_pos": fp,
                    "fix_family": fam,
                    "fix_voice": (r.get("fix_voice") or r.get("voice") or "").strip(),
                    "note": (r.get("note") or "").strip(),
                    "audit_note": f"p2-reconfirm:{p.name}",
                }
            )
    by = {f["literal"]: f for f in fixes}
    print("unique p2 fixes", len(by))
    print(upsert_ssot_rows(list(by.values()), note_suffix="p2-gate-reconfirm"))
    write_carrier()


if __name__ == "__main__":
    main()
