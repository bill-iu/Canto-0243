"""P1 follow-up cleanup: verb-suffix false v, cow-nv demote, high-freq u heuristics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ingest.project_pos import (
    DEFAULT_META,
    DEFAULT_TSV,
    PosRow,
    load_meta,
    parse_project_pos_tsv,
    pos_trust,
    write_carrier,
)
from ingest.project_pos_p1 import load_p1_mother_body, p1_status, update_meta_p1

ROOT = Path(__file__).resolve().parents[1]

# Weak endings removed from live heuristic but still on old SSOT rows
_WEAK_END = set("好上下來去過起")

# Explicit reclass for residual verb-suffix pure-v (from audit + expand)
_VERB_SUFFIX_FIX: Dict[str, str] = {
    # audit + common false v
    "也好": "x",
    "以上": "x",
    "以下": "x",
    "之上": "x",
    "之下": "x",
    "原來": "r",
    "從來": "r",
    "向來": "r",
    "一來": "r",
    "以來": "r",
    "只好": "r",
    "越來": "r",
    "不好": "a",
    "剛好": "a,r",
    "更好": "a",
    "幾好": "a",
    "仲好": "a",
    "世上": "n",
    "手上": "n",
    "不過": "r,x",
    "上下": "n,v",
    "右上": "n",
    "兩下": "r,x",
    "一去": "v",  # keep directional/event
    "做好": "v",
    "修好": "v",
    "做過": "v",
    "去過": "v",
    "問過": "v",
    "上來": "v",
    "上去": "v",
    "下去": "v",
    "入去": "v",
    "傳來": "v",
    "停下": "v",
    "卸下": "v",
    "加上": "v",
    "勾起": "v",
    "包起": "v",
    "問下": "v",
    "傾下": "v",
    "兜過": "v",
    "唔好": "a,v",
    "不起": "v",  # complement
    "下下": "r,x",
    "咗去": "u",
    "咗好": "u",
    "向上下": "x",  # skip if not exist
    "向下": "x,v",
    "向上": "x,v",
}

# High-frequency Cantonese closed-class / common words (P1 top-u)
_P1_U_HEURISTIC: Dict[str, str] = {
    "我": "x",
    "你": "x",
    "佢": "x",
    "好": "a,r",
    "呢": "x",
    "嘅": "x",
    "個": "x",
    "啦": "x",
    "噉": "r,x",
    "咁": "r,x",
    "啲": "x",
    "㗎": "x",
    "呀": "x",
    "既": "x",  # often 嘅/既 confusable particle
    "咗": "x",
    "咩": "x",
    "冇": "v,x",
    "去": "v",
    "左": "x,v",  # often 咗
    "得": "v,x",
    "嘢": "n",
    "喇": "x",
    "嚟": "v",
    "嗰": "x",
    "喎": "x",
    "哋": "x",
    "啊": "x",
    "先": "r,x",
    "乜": "x",
    "自己": "x",
    "隻": "x",
    "知": "v",
    "畀": "v,x",
    "咪": "x,v",
    "囉": "x",
    "因爲": "x",
    "因為": "x",
    "之後": "r,x",
    "上": "n,v,x",
    "好似": "v,r",
    "但係": "x",
    "下": "n,v,x",
    "搵": "v",
    "仲": "r,x",
    "哦": "x",
    "點解": "x,r",
    "諗": "v",
    "著": "v,x",
    "大": "a",
    "其實": "r",
    "嘩": "x",
    "出": "v",
    "快": "a,r",
    "只": "r,x",
    "然後": "r,x",
    "即係": "x,r",
    "返": "v",
    "屋企": "n",
    "鍾意": "v",
    "事": "n",
    "嘛": "x",
    "衫": "n",
    "唔到": "x,v",
    "拎": "v",
    "緊": "x,a",
    "瞓": "v",
    "邊度": "x",
    "亦": "r,x",
    "野": "n",  # 嘢 variant
    "搞": "v",
    "吓": "x",
    "係咪": "x,v",
    "呵呵": "x",
    "仔": "n",
    "驚": "v,a",
    "行": "v,n",
    "入面": "n,r",
    "一樣": "a,r",
    "阿": "x",
    "起": "v,x",
    # top-100 residual cow-single / demoted nv — clear classes
    "到": "v,x",
    "睇": "v",
    "地": "n,x",
    "住": "v,x",
    "要": "v,x",
    "會": "v,x",
    "人": "n",
    "話": "n,v",
    "做": "v",
    "食": "v",
    "講": "v",
    "想": "v",
    "一個": "n,x",
    "比": "v,x",
    "見": "v",
    "聽": "v",
    "叫": "v",
    "玩": "v",
    "幫": "v",
    "姐姐": "n",
    "入": "v",
    "完": "v,a",
    "埋": "v,x",
    "度": "n,x",
}


def _rewrite_table(table: Dict[str, PosRow], tsv: Path = DEFAULT_TSV) -> None:
    lines = ["literal\tpos\tfamily\tvoice\tnote"]
    for lit in sorted(table.keys()):
        row = table[lit]
        lines.append(
            f"{lit}\t{','.join(sorted(row.pos))}\t{row.family}\t{row.voice}\t{row.note}"
        )
    tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _set_pos(
    table: Dict[str, PosRow],
    lit: str,
    pos_csv: str,
    *,
    note_extra: str,
    family: str = "",
    voice: str = "",
) -> bool:
    row = table.get(lit)
    if not row:
        # allow create for u-promote of p1 words not... they're always in table
        return False
    parts = [p.strip() for p in pos_csv.replace("|", ",").split(",") if p.strip()]
    pos = frozenset(parts)
    note = row.note
    have = {t.strip() for t in note.split(";") if t.strip()}
    for bit in note_extra.split(";"):
        bit = bit.strip()
        if bit and bit not in have:
            note = f"{note};{bit}" if note else bit
            have.add(bit)
    table[lit] = PosRow(
        literal=lit,
        pos=pos,
        family=family if family else row.family,
        voice=voice if voice else row.voice,
        note=note,
    )
    return True


def cleanup_verb_suffix(table: Dict[str, PosRow]) -> dict:
    fixed = 0
    skipped = 0
    for lit, row in list(table.items()):
        if "verb-suffix" not in row.note:
            continue
        if "review" in row.note and "p1-cleanup" not in row.note:
            # already human/audit reviewed — skip unless still pure-v weak end and no p1-audit
            if "p1-audit" in row.note:
                skipped += 1
                continue
        if len(lit) != 2 or lit[-1] not in _WEAK_END:
            skipped += 1
            continue
        if row.pos != frozenset({"v"}):
            skipped += 1
            continue
        if lit in _VERB_SUFFIX_FIX:
            _set_pos(table, lit, _VERB_SUFFIX_FIX[lit], note_extra="p1-cleanup;verb-suffix-fix;review")
            fixed += 1
            continue
        # pattern rules
        if lit.endswith(("以上", "以下", "之上", "之下")):
            _set_pos(table, lit, "x", note_extra="p1-cleanup;verb-suffix-fix;review")
            fixed += 1
        elif lit[-1] in "上下" and lit[0] in "手牀床桌地天世身臉面口":
            _set_pos(table, lit, "n", note_extra="p1-cleanup;verb-suffix-fix;review")
            fixed += 1
        elif lit.endswith(("原來", "從來", "向來", "一來", "以來", "本來")):
            _set_pos(table, lit, "r", note_extra="p1-cleanup;verb-suffix-fix;review")
            fixed += 1
        elif lit[-1] == "好" and lit[0] in "不幾更仲只剛":
            _set_pos(table, lit, "a" if lit[0] != "只" else "r", note_extra="p1-cleanup;verb-suffix-fix;review")
            fixed += 1
        else:
            # demote remaining weak pure-v to low-trust undetermined-ish: keep v but mark low
            # better: leave for later; only demote trust via note
            note = row.note
            if "verb-suffix-suspect" not in note:
                table[lit] = PosRow(
                    literal=lit,
                    pos=row.pos,
                    family=row.family,
                    voice=row.voice,
                    note=f"{note};verb-suffix-suspect",
                )
                # force low trust: append cow-single-like marker
                # use explicit low note tag
                r2 = table[lit]
                table[lit] = PosRow(
                    literal=lit,
                    pos=r2.pos,
                    family=r2.family,
                    voice=r2.voice,
                    note=f"{r2.note};trust-low",
                )
                fixed += 1  # trust demotion counts
            else:
                skipped += 1
    return {"fixed_or_demoted": fixed, "skipped": skipped}


def demote_cow_nv(table: Dict[str, PosRow]) -> dict:
    """Exact {n,v} cow-multi → low trust (draft), keep codes for later review."""
    n = 0
    for lit, row in list(table.items()):
        if "cow-multi" not in row.note:
            continue
        if row.pos != frozenset({"n", "v"}):
            continue
        if "review" in row.note:
            continue
        note = row.note.replace("cow-multi", "cow-nv-unreviewed")
        if "cow-nv-unreviewed" not in note:
            note = f"{note};cow-nv-unreviewed"
        if "trust-low" not in note:
            note = f"{note};trust-low"
        table[lit] = PosRow(
            literal=lit,
            pos=row.pos,
            family=row.family,
            voice=row.voice,
            note=note,
        )
        n += 1
    return {"demoted_nv": n}


def promote_p1_u_heuristics(table: Dict[str, PosRow]) -> dict:
    body = set(load_p1_mother_body())
    n = 0
    for lit, pos_csv in _P1_U_HEURISTIC.items():
        if lit not in body:
            continue
        row = table.get(lit)
        if not row:
            continue
        if row.gate_pos() and "canto-heuristic" not in row.note:
            # already gate-worthy from other high-trust source
            if row.trust() == "high":
                continue
        # promote u or any non-high-gate (incl. cow-single / demoted nv)
        if row.trust() == "high" and row.gate_pos():
            continue
        _set_pos(
            table,
            lit,
            pos_csv,
            note_extra="p1-cleanup;canto-heuristic;review",
        )
        n += 1
    return {"promoted": n}


def run_all() -> dict:
    table = parse_project_pos_tsv()
    stats = {
        "verb_suffix": cleanup_verb_suffix(table),
        "cow_nv": demote_cow_nv(table),
        "p1_u": promote_p1_u_heuristics(table),
    }
    _rewrite_table(table)
    write_carrier()
    st = p1_status()
    update_meta_p1(st, k=5000)
    meta = load_meta()
    meta["version"] = "0.1.4"
    meta["p1_cleanup"] = stats
    meta["p1"] = {
        **(meta.get("p1") or {}),
        **{
            "gate_formal": st["gate_formal"],
            "gate_coverage": st["gate_coverage"],
            "undetermined_only": st["undetermined_only"],
            "complete": st["p1_complete"],
        },
    }
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stats["p1_status"] = st
    # sanity: trust-low must be low
    sample = next((r for r in table.values() if "trust-low" in r.note), None)
    if sample:
        stats["trust_low_check"] = pos_trust(sample.note)
    return stats


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_cleanup")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="verb-suffix fix + cow-nv demote + p1 u heuristics")
    args = p.parse_args(argv)
    if args.cmd == "run":
        print(json.dumps(run_all(), ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
