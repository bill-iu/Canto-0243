"""Human-style residual filter over alias_proposals.tsv — print decisions."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from ingest.project_pos import parse_project_pos_tsv
from ingest.project_pos_alias import alias_map

ROOT = Path(__file__).resolve().parents[4]
PROP = ROOT / "data" / "pos" / "alias_proposals.tsv"

# Free morphemes — NEVER residual (common singles that form many compounds)
FREE_MORPHEME = set(
    "上下中大小好不好來去過起前後內外高低長短新舊黑白紅青山水火土金木人手足口耳目心頭身力氣金銀銅鐵水電風雨雪月日天"
    "功成敗失開關進出有無可否是非真假高低多少遠近深淺厚薄輕重冷熱乾濕"
    "京劇悲功協否始姿孤廉悲戒暴消測滋獨維設優創"
)

# Accept only when source is bound half of a fixed binome (rare free use).
# Hand list from high-score proposals + known true residuals already in alias.
ACCEPT: list[tuple[str, str, str]] = [
    # already in alias.tsv — skip if present
    # additional true residuals if any appear in proposals:
    # (none automatic from 京+劇 style)
]

# Reject examples for documentation (auto-pair noise)
# 京→京劇, 功→功夫, 悲→悲劇, 維→維護, 創→創造, etc.


def main() -> None:
    table = parse_project_pos_tsv()
    have = alias_map()
    rows = list(csv.DictReader(PROP.open(encoding="utf-8"), delimiter="\t"))
    by_tgt: dict[str, list] = defaultdict(list)
    for r in rows:
        by_tgt[r["target"]].append(r)

    hi = [r for r in rows if float(r["score"]) >= 1.0]
    print(f"proposals={len(rows)} score>=1={len(hi)} existing_alias={len(have)}")
    print("--- high score (manual verdict) ---")
    accept_n = reject_n = 0
    for r in sorted(hi, key=lambda x: (x["target"], x["source"])):
        src, tgt = r["source"], r["target"]
        if src in have:
            print(f"SKIP already {src}->{have[src]}")
            continue
        sr = table.get(src)
        tr = table.get(tgt)
        # Heuristic hard reject: source is free morpheme OR source length!=1
        if len(src) != 1:
            verdict = "REJECT len"
            reject_n += 1
        elif src in FREE_MORPHEME or any(c in FREE_MORPHEME for c in src):
            # single char in free set
            if src in FREE_MORPHEME or src in set("".join(FREE_MORPHEME)):
                verdict = "REJECT free-morpheme"
                reject_n += 1
            else:
                verdict = "REVIEW"
        else:
            # only accept if BOTH halves of tgt are still u singles and rarely free —
            # default REJECT for auto-pair; true residuals already seeded
            verdict = "REJECT default-auto-pair"
            reject_n += 1
        spos = ",".join(sorted(sr.pos)) if sr else "-"
        tpos = ",".join(sorted(tr.pos)) if tr else "-"
        print(f"{verdict}\t{src}->{tgt}\tsrc={spos}\ttgt={tpos}")

    print(f"--- accept={accept_n} reject={reject_n} ---")
    print("Policy: no new alias from auto-pair this round; seed list remains authoritative.")
    print("True residuals still missing? Scan essay u singles with bound-char evidence.")


if __name__ == "__main__":
    main()
