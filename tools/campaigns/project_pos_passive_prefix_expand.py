"""Expand passive-prefix SSOT + proposals (grill 2026-07-22).

- Pipeline: PASSIVE_PREFIXES + COW keeps pos / merges voice (project_pos_p0).
- SSOT: agent-reviewed high-confidence fills; full scan → proposals TSV.
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

from tools.campaigns._repo import REPO_ROOT as ROOT
from ingest.project_pos import (
    DEFAULT_TSV,
    PASSIVE_PREFIXES,
    TSV_HEADER,
    parse_project_pos_tsv,
    write_carrier,
)
from tools.campaigns.project_pos_p0 import load_cow_pos_map, propose_for_literal

PROPOSALS = ROOT / "data" / "pos" / "proposals" / "passive_prefix_expand.tsv"
NOTE_TAG = "passive-prefix-expand;review"
# Agent-reviewed seeds: literal → preferred pos (被動義名詞可 n).
SEED_PASSIVE: dict[str, str] = {
    "獲救": "v",
    "得救": "v",  # 得* 構詞；prefix 含「得」
    "遇救": "v",
    "獲釋": "v",
    "獲益": "n",  # 被動義名詞
    "受益": "v",
    "受阻": "v",
    "遭難": "v",
    "被捕": "v",
    "被殺": "v",
    "捱打": "v",
    "遭殃": "v",
    # 被動義角色／結果名詞
    "受害人": "n",
    "受害者": "n",
    "受益人": "n",
    "被害人": "n",
}
# Non-suffering / technical — never force voice.
SKIP_VOICE = frozenset(
    {
        "被窩",
        "被套",  # 被褥類
        "被告人",
        "被上訴人",  # 法律程序角色，唔當遭受義被動名
        "受衆",
        "被子植物",
        "被子植物門",
        "被動免疫",
        "受孕",
        "被動",  # 詞彙「passive」本身
        "被乘數",
        "被加數",
        "被除數",
        "被單",
        "被面",
        "被告",  # 法律角色名；唔當遭受構詞
    }
)
# Auto SSOT morph fill: 叫給讓 只提案；「得」只靠 seed／審核，唔盲灌（得到／得意…）
AUTO_SSOT_PREFIXES = frozenset("被捱受遭獲挨")


def _lexicon_chars(db: Path) -> set[str]:
    con = sqlite3.connect(str(db))
    try:
        rows = con.execute("SELECT char FROM words").fetchall()
    finally:
        con.close()
    return {r[0] for r in rows if r[0]}


def _formal(pos: str) -> set[str]:
    return {p.strip() for p in (pos or "").replace("|", ",").split(",") if p.strip()}


def _should_auto_ssot(lit: str, pos: str) -> bool:
    if lit in SKIP_VOICE:
        return False
    if lit in SEED_PASSIVE:
        return True
    if len(lit) < 2 or lit[0] not in AUTO_SSOT_PREFIXES:
        return False
    tags = _formal(pos)
    if not tags:
        return True
    # 動詞／形；被動義名詞靠 SEED（如獲益），唔自動全收 n
    if "v" in tags or "a" in tags:
        return True
    return False


def main() -> int:
    db = ROOT / "lyrics.db"
    if not db.is_file():
        print("missing lyrics.db", file=sys.stderr)
        return 1
    lex = _lexicon_chars(db)
    table = parse_project_pos_tsv()
    cow = load_cow_pos_map()

    # --- scan proposals (all prefixes) ---
    proposal_rows: list[dict] = []
    for lit in sorted(lex):
        if len(lit) < 2 or lit[0] not in PASSIVE_PREFIXES:
            continue
        prop = propose_for_literal(lit, cow=cow)
        if not prop:
            continue
        pos, family, voice, note, source, conf = prop
        if voice != "passive":
            continue
        existing = table.get(lit)
        if existing and existing.voice == "passive":
            continue
        proposal_rows.append(
            {
                "literal": lit,
                "pos": pos if not existing else ",".join(sorted(existing.pos)),
                "family": family if not existing else existing.family,
                "voice": "passive",
                "note": note,
                "source": source if not existing else "ssot-patch",
                "confidence": conf,
                "prior_voice": existing.voice if existing else "",
                "status": "missing" if not existing else "empty_voice",
            }
        )

    PROPOSALS.parent.mkdir(parents=True, exist_ok=True)
    with PROPOSALS.open("w", encoding="utf-8", newline="") as fh:
        fields = [
            "literal",
            "pos",
            "family",
            "voice",
            "note",
            "source",
            "confidence",
            "prior_voice",
            "status",
        ]
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in proposal_rows:
            w.writerow(row)
    print(f"proposals {len(proposal_rows)} → {PROPOSALS}")

    # --- agent-reviewed SSOT apply ---
    from ingest.project_pos import PosRow, split_pos

    changed = 0
    # Seeds first (explicit pos, incl. passive nouns)
    for lit, want_pos in SEED_PASSIVE.items():
        if lit not in lex:
            print(f"skip seed not in lexicon: {lit}")
            continue
        note = f"prefix-passive;heuristic;{NOTE_TAG}"
        if lit in table:
            row = table[lit]
            # prefer seed pos when current lacks want, else keep richer set
            tags = set(row.pos)
            if want_pos not in tags and tags <= {"u", "n", "x"} and want_pos == "v":
                tags = {want_pos}
            elif want_pos not in tags and want_pos == "n" and not tags:
                tags = {want_pos}
            elif want_pos == "n" and tags <= {"n"}:
                tags = {"n"}
            elif want_pos == "v" and "v" not in tags:
                tags = {want_pos} if not tags or tags <= {"u", "n"} else tags | {"v"}
            keep_pos = ",".join(sorted(tags)) if tags else want_pos
            if row.voice == "passive" and keep_pos == ",".join(sorted(row.pos)):
                continue
            table[lit] = PosRow(
                literal=lit,
                pos=split_pos(keep_pos),
                family=row.family,
                voice="passive",
                note=f"{row.note};{note}".strip(";"),
            )
        else:
            table[lit] = PosRow(
                literal=lit,
                pos=split_pos(want_pos),
                family="",
                voice="passive",
                note=note,
            )
        changed += 1
        print(f"seed {lit} pos={want_pos}")

    # Existing empty-voice + safe prefix + not skip
    for lit, row in list(table.items()):
        if row.voice == "passive":
            continue
        if lit in SEED_PASSIVE:
            continue
        if not _should_auto_ssot(lit, ",".join(sorted(row.pos))):
            continue
        note = f"{row.note};prefix-passive;{NOTE_TAG}".strip(";")
        table[lit] = PosRow(
            literal=lit,
            pos=row.pos,
            family=row.family,
            voice="passive",
            note=note,
        )
        changed += 1

    # New absents: safe prefix, proposed v/a, in lex
    for lit in sorted(lex):
        if lit in table:
            continue
        if lit in SEED_PASSIVE:
            continue
        if not _should_auto_ssot(lit, "v"):
            continue
        prop = propose_for_literal(lit, cow=cow)
        if not prop or prop[2] != "passive":
            continue
        pos, family, _v, note, _src, _conf = prop
        tags = _formal(pos)
        if "v" not in tags and "a" not in tags:
            continue
        if "u" in tags and "v" not in tags:
            pos = "v"
        table[lit] = PosRow(
            literal=lit,
            pos=split_pos(pos if pos != "u" else "v"),
            family=family,
            voice="passive",
            note=f"{note};{NOTE_TAG}",
        )
        changed += 1

    # Clear known false-positive passive voice (noun / non-suffering)
    for lit in SKIP_VOICE:
        row = table.get(lit)
        if not row or row.voice != "passive":
            continue
        table[lit] = PosRow(
            literal=lit,
            pos=row.pos,
            family=row.family,
            voice="",
            note=f"{row.note};clear-false-passive-voice;review".strip(";"),
        )
        changed += 1

    # Write TSV sorted
    path = DEFAULT_TSV
    rows = sorted(table.values(), key=lambda r: r.literal)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(TSV_HEADER), delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "literal": r.literal,
                    "pos": ",".join(sorted(r.pos)),
                    "family": r.family,
                    "voice": r.voice,
                    "note": r.note,
                }
            )
    print(f"ssot changed≈{changed} rows now={len(rows)} → {path}")
    out = write_carrier()
    print(f"carrier → {out}")
    # verify 獲救
    t2 = parse_project_pos_tsv()
    r = t2.get("獲救")
    print("獲救", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
