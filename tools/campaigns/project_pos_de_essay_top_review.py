"""Essay-top review of 得* hold proposals; apply only clear passives.

得到／叫好 明確非被動。得* 多數為能願／程度／主動獲得。
"""
from __future__ import annotations

import csv
from pathlib import Path

from tools.campaigns._repo import REPO_ROOT as ROOT
from ingest.project_pos import (
    DEFAULT_TSV,
    TSV_HEADER,
    PosRow,
    parse_project_pos_tsv,
    split_pos,
    write_carrier,
)

ESSAY = ROOT / "data" / "essay" / "essay-cantonese.txt"
HOLD_SRC = ROOT / "data" / "pos" / "proposals" / "passive_prefix_expand_review.tsv"
OUT = ROOT / "data" / "pos" / "proposals" / "passive_de_essay_top_review.tsv"
NOTE = "passive-de-essay-top;review"
TOP_N = 60

# Clear passive / passive-noun (this batch)
ACCEPT: dict[str, str] = {
    "得益": "n",  # ≈ 受益／獲益
    "得益於": "v",  # 受惠於
    "得寵": "v",  # 被寵
    "得濟": "v",  # 得救助／緩解
    "得救": "v",  # already; keep
}

# User-explicit non-passive + high-freq false friends
REJECT_EXPLICIT = frozenset(
    {
        "得到",
        "叫好",
        # degree / modal / aspect (Cantonese 得)
        "得多",
        "得很",
        "得滯",
        "得切",
        "得個",
        "得嚟",
        "得嗰",
        "得閒",
        "得空",
        "得落",
        "得着",
        "得著",
        # attain / win / know
        "得知",
        "得悉",
        "得出",
        "得獎",
        "得獎者",
        "得獎人",
        "得勝",
        "得逞",
        "得票",
        "得標",
        "得手",
        "得勢",
        "得志",
        "得道",
        "得名",
        "得法",
        "得用",
        "得力",
        "得宜",
        "得當",
        "得體",
        "得病",
        "得罪",
        "得主",
        "得人",
        "得人心",
        "得數",
        "得計",
        "得失",
        "得米",
        "得無",
        # idioms / active evaluative
        "得不償失",
        "得寸進尺",
        "得過且過",
        "得天獨厚",
        "得心應手",
        "得意洋洋",
        "得意忘形",
        "得意揚揚",
        "得來不易",
        "得來全不費功夫",
        "得來速",
        "得償所願",
        "得而復失",
        "得隴望蜀",
        "得魚忘筌",
        "得失參半",
        "得饒人處且饒人",
        "得理不饒人",
        "得道多助",
        "得其所哉",
        "得意門生",
        "得力助手",
        "得人驚",
        "得人憎",
        "得人怕",
        "得戚",
        "得過",  # 過得／得過且過 fragment sense
        "得把聲",
        "得個講字",
        "得時",
        "得克薩斯州",
    }
)


def load_essay() -> dict[str, int]:
    out: dict[str, int] = {}
    for line in ESSAY.read_text(encoding="utf-8").splitlines():
        if "\t" not in line:
            continue
        w, c = line.split("\t", 1)
        try:
            out[w] = int(c.strip() or 0)
        except ValueError:
            continue
    return out


def main() -> int:
    essay = load_essay()
    rank = {
        w: i + 1
        for i, (w, _) in enumerate(sorted(essay.items(), key=lambda x: -x[1]))
    }

    if not HOLD_SRC.is_file():
        print("missing", HOLD_SRC)
        return 1
    rows = list(csv.DictReader(HOLD_SRC.open(encoding="utf-8"), delimiter="\t"))
    hold = [r for r in rows if r.get("verdict") == "hold" and r["literal"].startswith("得")]
    scored = []
    for r in hold:
        lit = r["literal"]
        c = essay.get(lit, 0)
        scored.append((c, rank.get(lit, 10**9), r))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]["literal"]))
    # Prefer with essay mass; fill to TOP_N
    with_c = [s for s in scored if s[0] > 0]
    batch = with_c[:TOP_N]
    if len(batch) < TOP_N:
        batch = scored[:TOP_N]

    out_rows = []
    for c, rk, r in batch:
        lit = r["literal"]
        if lit in ACCEPT:
            verdict, reason = "accept", f"被動／受惠義 → pos={ACCEPT[lit]}"
        elif lit in REJECT_EXPLICIT or lit == "得到":
            verdict, reason = "reject", "能願／程度／主動獲得／成語；非被動構詞"
        elif any(lit.endswith(s) for s in ("救", "釋", "赦", "寵", "益", "賜", "封", "賞", "濟")):
            verdict, reason = "accept", "得+受惠／得救類後綴"
            ACCEPT.setdefault(lit, "v")
        else:
            verdict, reason = "reject", "Essay-top 預設 reject（得≠被動）"
        out_rows.append(
            {
                "literal": lit,
                "essay_count": c,
                "essay_rank": "" if rk >= 10**9 else rk,
                "pos_proposal": r.get("pos", ""),
                "verdict": verdict,
                "reason": reason,
            }
        )

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=list(out_rows[0].keys()),
            delimiter="\t",
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(out_rows)

    table = parse_project_pos_tsv()
    applied: list[str] = []
    for row in out_rows:
        if row["verdict"] != "accept":
            continue
        lit = row["literal"]
        want = ACCEPT.get(lit, "v")
        ex = table.get(lit)
        if ex and ex.voice == "passive":
            continue
        if ex:
            pos = ex.pos
            if want == "n" and pos <= frozenset({"u"}):
                pos = split_pos("n")
            elif want == "v" and "v" not in pos and pos <= frozenset({"u", "n"}):
                pos = split_pos("v")
            table[lit] = PosRow(
                literal=lit,
                pos=pos,
                family=ex.family,
                voice="passive",
                note=f"{ex.note};prefix-passive;{NOTE}".strip(";"),
            )
        else:
            table[lit] = PosRow(
                literal=lit,
                pos=split_pos(want),
                family="",
                voice="passive",
                note=f"prefix-passive;{NOTE}",
            )
        applied.append(f"{lit}:{want}")

    with DEFAULT_TSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(TSV_HEADER), delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in sorted(table.values(), key=lambda x: x.literal):
            w.writerow(
                {
                    "literal": r.literal,
                    "pos": ",".join(sorted(r.pos)),
                    "family": r.family,
                    "voice": r.voice,
                    "note": r.note,
                }
            )
    write_carrier()

    vc = {k: sum(1 for r in out_rows if r["verdict"] == k) for k in ("accept", "reject")}
    print(f"essay-top batch {len(out_rows)} → {OUT}")
    print("verdicts", vc)
    print("applied", applied)
    print("---")
    for r in out_rows:
        tag = "Y" if r["verdict"] == "accept" else "N"
        print(f"{tag}\t{r['essay_count']}\t{r['literal']}\t{r['reason'][:48]}")
    t = parse_project_pos_tsv()
    for lit in ("得到", "得救", "得益", "得益於", "得寵", "得濟", "叫好", "得多", "得獎"):
        r = t.get(lit)
        print("ssot", lit, (r.voice if r else None), (sorted(r.pos) if r else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
