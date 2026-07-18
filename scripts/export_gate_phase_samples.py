"""Export gate-only samples per phase after full_r1 apply (for quality re-confirm)."""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from ingest.project_pos import parse_project_pos_tsv
from ingest.project_pos_audit import sample_size_for
from ingest.project_pos_p0 import load_p0_mother_body
from ingest.project_pos_p1 import load_p1_mother_body
from ingest.project_pos_p2 import load_p2_body
from ingest.project_pos_p3 import load_p3_body

SEED = 20260720
OUT = Path("data/pos/audit/full_r1/gate_reconfirm")


def export(name: str, universe: list[str], t, rng: random.Random) -> dict:
    n = sample_size_for(len(universe))
    sample = sorted(rng.sample(universe, n)) if n < len(universe) else sorted(universe)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}_gate_sample.tsv"
    header = [
        "phase",
        "literal",
        "pos",
        "family",
        "voice",
        "note",
        "trust",
        "stratum",
        "verdict",
        "fix_pos",
        "fix_family",
        "fix_voice",
        "audit_note",
    ]
    rows = []
    for lit in sample:
        r = t[lit]
        rows.append(
            {
                "phase": name,
                "literal": lit,
                "pos": ",".join(sorted(r.pos)),
                "family": r.family,
                "voice": r.voice,
                "note": r.note,
                "trust": r.trust(),
                "stratum": "gate",
                "verdict": "",
                "fix_pos": "",
                "fix_family": "",
                "fix_voice": "",
                "audit_note": "",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    meta = {"phase": name, "universe": len(universe), "sample_n": n, "seed": SEED, "out": str(path)}
    path.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False))
    return meta


def main() -> None:
    rng = random.Random(SEED)
    t = parse_project_pos_tsv()
    p0 = [lit for lit in load_p0_mother_body() if lit in t and t[lit].gate_pos()]
    p1 = [lit for lit in load_p1_mother_body() if lit in t and t[lit].gate_pos()]
    p2 = [
        lit
        for lit, _ in load_p2_body()
        if lit in t and t[lit].family == "idiom" and t[lit].trust() == "high"
    ]
    p3 = [lit for _, lit in load_p3_body() if lit in t and t[lit].gate_pos()]
    metas = [
        export("p0", p0, t, rng),
        export("p1", p1, t, rng),
        export("p2", p2, t, rng),
        export("p3", p3, t, rng),
    ]
    (OUT / "manifest.json").write_text(
        json.dumps({"seed": SEED, "phases": metas}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
