import csv
import math
import random
from pathlib import Path

from ingest.project_pos import parse_project_pos_tsv

table = parse_project_pos_tsv()
universe = [
    lit
    for lit, r in table.items()
    if "u-inlex-idiom" in (r.note or "") and r.pos != frozenset({"u"})
]
n = min(len(universe), max(50, math.ceil(len(universe) * 0.05)))
rng = random.Random(7)
sample = sorted(rng.sample(universe, n)) if n < len(universe) else sorted(universe)
out = Path("data/pos/audit/u_inlex/u_inlex_idiom_gate_r1.tsv")
header = [
    "literal",
    "pos",
    "family",
    "voice",
    "note",
    "trust",
    "verdict",
    "fix_pos",
    "fix_family",
    "audit_note",
]
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
                "fix_family": "",
                "audit_note": "",
            }
        )
print("sample", n, "universe", len(universe), "->", out)
for lit in sample:
    r = table[lit]
    print(lit, ",".join(sorted(r.pos)), r.family)
