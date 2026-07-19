# -*- coding: utf-8 -*-
"""Merge p0_sample_part{1-5}.tsv → p0_sample.tsv"""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
HEADER = [
    "phase", "literal", "pos", "family", "voice", "note", "trust", "stratum",
    "verdict", "fix_pos", "fix_family", "fix_voice", "audit_note",
]
rows = []
for i in range(1, 6):
    p = ROOT / f"p0_sample_part{i}.tsv"
    with p.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append({k: r.get(k, "") for k in HEADER})
out = ROOT / "p0_sample.tsv"
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
from collections import Counter
c = Counter(r["verdict"] for r in rows)
print(len(rows), dict(c), "empty", sum(1 for r in rows if not r["verdict"]))
