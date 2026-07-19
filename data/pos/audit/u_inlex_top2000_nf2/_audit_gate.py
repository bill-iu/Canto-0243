"""G1 audit nf2 batch sample."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from ingest.project_pos import PosRow, parse_project_pos_tsv, write_carrier
from ingest.project_pos_alias import _with_tokens
from ingest.project_pos_audit import apply_verdicts_file, upsert_ssot_rows
from ingest.project_pos_cleanup import _rewrite_table

DIR = Path(__file__).resolve().parent
PATH = DIR / "nf2k_gate_r1.tsv"

# Default OK; only list exceptions
SOFT = {
    "心有靈犀": "a 主；n 弱",
    "驗": "v 主；亦可 n",
    "單方面": "多標可",
    "貳": "大寫數／虛",
}
BAD = {
    "一脈相承": ("a,r", "成語偏 a/r；v 假陽"),
}


def main() -> None:
    rows = list(csv.DictReader(PATH.open(encoding="utf-8"), delimiter="\t"))
    c = Counter()
    out = []
    for r in rows:
        lit = r["literal"]
        if lit in BAD:
            v, fp, note = "BAD", BAD[lit][0], BAD[lit][1]
        elif lit in SOFT:
            v, fp, note = "SOFT", "", SOFT[lit]
        else:
            v, fp, note = "OK", "", ""
        r["verdict"] = v
        r["fix_pos"] = fp
        r["audit_note"] = note
        c[v] += 1
        out.append(r)
    n = sum(c.values())
    rate = (c["OK"] + c["SOFT"]) / n
    print(dict(c), "ok_rate", round(rate, 4), "PASS" if rate >= 0.90 else "FAIL")
    with PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print("apply", apply_verdicts_file(PATH, dry_run=False))

    table = parse_project_pos_tsv()
    for lit, kind, note in [
        ("國內生產", "clause-slice", "國內生產總值殘片"),
        ("踊", "residual", "踊躍殘字；完整詞未入 SSOT"),
    ]:
        row = table.get(lit)
        if not row:
            continue
        table[lit] = PosRow(
            lit, frozenset({"u"}), row.family, row.voice, _with_tokens(row.note, "fragment", kind, note)
        )
    _rewrite_table(table)
    write_carrier()
    print("tagged keep-u fragments")


if __name__ == "__main__":
    main()
