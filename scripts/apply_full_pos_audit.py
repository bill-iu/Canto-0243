"""Apply all BAD fixes from full_r1 audit TSVs."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from ingest.project_pos import PosRow, parse_project_pos_tsv, write_carrier
from ingest.project_pos_audit import upsert_ssot_rows
from ingest.project_pos_cleanup import _rewrite_table

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data" / "pos" / "audit" / "full_r1"


def collect_files() -> list[Path]:
    files: list[Path] = []
    files.extend(sorted(FULL.glob("p0_sample_part*.tsv")))
    for name in ("p1_sample.tsv", "p2_idiom_sample.tsv"):
        p = FULL / name
        if p.is_file():
            files.append(p)
    files.extend(sorted(FULL.glob("p3_sample_part*.tsv")))
    return files


def main() -> None:
    files = collect_files()
    pos_fixes: list[dict] = []
    family_clears: set[str] = set()
    stats = Counter()
    for path in files:
        rows = list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))
        for r in rows:
            v = (r.get("verdict") or "").strip().upper()
            if v in ("OK", "PASS"):
                stats["ok"] += 1
            elif v in ("SOFT", "SOFT-OK"):
                stats["soft"] += 1
            elif v in ("BAD", "FIX"):
                stats["bad"] += 1
                lit = (r.get("literal") or "").strip()
                if not lit:
                    continue
                fp = (r.get("fix_pos") or "").strip()
                ff_raw = r.get("fix_family")
                # Explicit empty fix_family on idiom row → clear family
                if (
                    (r.get("family") or "") == "idiom"
                    and ff_raw is not None
                    and str(ff_raw).strip() in ("", "none", "-", "empty", "普通")
                ):
                    family_clears.add(lit)
                if fp:
                    # keep idiom if not clearing
                    fam = (r.get("family") or "").strip()
                    if lit in family_clears:
                        fam = ""
                    elif ff_raw is not None and str(ff_raw).strip() not in ("", "none"):
                        fam = str(ff_raw).strip()
                    pos_fixes.append(
                        {
                            "literal": lit,
                            "fix_pos": fp,
                            "fix_family": fam,
                            "fix_voice": (r.get("fix_voice") or r.get("voice") or "").strip(),
                            "note": (r.get("note") or "").strip(),
                            "audit_note": (r.get("audit_note") or "full-r1").strip()[:80],
                        }
                    )
            else:
                stats["skip"] += 1

    n = stats["ok"] + stats["soft"] + stats["bad"]
    rate = (stats["ok"] + stats["soft"]) / n if n else 0.0
    print(
        json.dumps(
            {
                "audited": n,
                **dict(stats),
                "ok_rate_mixed": round(rate, 4),
                "pos_fixes": len(pos_fixes),
                "family_clears": len(family_clears),
            },
            ensure_ascii=False,
        )
    )

    up = upsert_ssot_rows(pos_fixes, note_suffix="full-r1-audit")
    print("upsert", up)

    table = parse_project_pos_tsv()
    cleared = 0
    for lit in family_clears:
        if lit not in table:
            continue
        row = table[lit]
        note = row.note
        if "full-r1-clear-idiom" not in note.split(";"):
            note = f"{note};full-r1-clear-idiom" if note else "full-r1-clear-idiom"
        table[lit] = PosRow(
            literal=lit,
            pos=row.pos,
            family="",
            voice=row.voice,
            note=note,
        )
        cleared += 1
    if cleared:
        _rewrite_table(table)
    write_carrier()
    print("family_cleared", cleared)


if __name__ == "__main__":
    main()
