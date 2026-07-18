"""P0 詞性覆蓋：凍結 campaign 頭尾母體、提案、合併、狀態（CONTEXT § 詞性覆蓋母體）。"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from ingest.project_pos import (
    ALL_POS,
    DEFAULT_META,
    DEFAULT_TSV,
    FORMAL_POS,
    ProjectPosError,
    load_meta,
    parse_project_pos_tsv,
    write_carrier,
    split_pos,
)

ROOT = Path(__file__).resolve().parents[1]
POS_DIR = ROOT / "data" / "pos"
P0_BODY = POS_DIR / "p0_mother_body.txt"
P0_PROPOSALS = POS_DIR / "proposals" / "p0_proposals.tsv"
COW_MAP = ROOT / "docs" / "research" / "cow-pos-map.json"

ANT_TSV = ROOT / "data" / "syn_ant" / "project_antonyms.tsv"
SYN_TSV = ROOT / "data" / "syn_ant" / "project" / "project_synonyms.tsv"
NN_ANT = ROOT / "data" / "syn_ant" / "project_no_natural_antonyms.tsv"
NN_SYN = ROOT / "data" / "syn_ant" / "project" / "project_no_natural_synonyms.tsv"
CAMP_HEAD_TSVS = (
    ROOT / "data" / "syn_ant" / "campaign_top5000.tsv",
    ROOT / "data" / "syn_ant" / "campaign_len4.tsv",
    ROOT / "data" / "syn_ant" / "campaign_len4_no_natural.tsv",
    ROOT / "data" / "syn_ant" / "project" / "campaign_syn_top5000.tsv",
    ROOT / "data" / "syn_ant" / "project" / "campaign_syn_len4.tsv",
)

PROPOSAL_HEADER = ("literal", "pos", "family", "voice", "note", "source", "confidence")

# Closed-class / high-frequency 虛·副 seeds (HK written); multi ok.
_HEURISTIC_POS: Dict[str, str] = {
    "的": "x",
    "了": "x",
    "喺": "x",
    "同": "x,v",
    "同埋": "x",
    "係": "v,x",
    "唔": "r,x",
    "唔係": "v,x",
    "已經": "r",
    "尚未": "r",
    "一定": "r,a",
    "未必": "r",
    "一齊": "r",
    "即刻": "r",
    "稍後": "r",
    "未": "r,x",
    "已": "r,x",
    "不": "r,x",
    "沒": "r,x",
    "無": "v,a,x",
    "有": "v",
    "是": "v,x",
    "在": "v,x",
    "和": "x",
    "與": "x",
    "及": "x",
    "或": "x",
    "但": "x",
    "而": "x",
    "並": "r,x",
    "也": "r,x",
    "都": "r,x",
    "就": "r,x,v",
    "才": "r,x",
    "還": "r,x",
    "再": "r",
    "又": "r,x",
    "很": "r",
    "太": "r",
    "更": "r",
    "最": "r",
    "非常": "r",
    "比較": "r,v",
    "因為": "x",
    "所以": "x",
    "如果": "x",
    "雖然": "x",
    "但是": "x",
    "而且": "x",
    "或者": "x",
    "還是": "x,r",
    "可以": "v,x",
    "應該": "v,x",
    "需要": "v,n",
    "能夠": "v,x",
    "把": "x,v",
    "被": "x",
    "將": "x,v",
    "對": "x,a,v",
    "向": "x,v",
    "從": "x",
    "由": "x",
    "為": "x,v",
    "以": "x",
    "於": "x",
    "給": "v,x",
    "讓": "v,x",
    "使": "v,x",
    "之": "x",
    "其": "x",
    "此": "x",
    "該": "x,v",
    "各": "x",
    "每": "x",
    "這": "x",
    "那": "x",
    "什麼": "x",
    "怎麼": "x,r",
    "怎樣": "x,r",
    "哪": "x",
    "誰": "x",
    "幾": "x",
    "多": "a,r",
    "少": "a,r",
}


def _tsv_literals(path: Path, cols: Sequence[str]) -> Set[str]:
    out: Set[str] = set()
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            for c in cols:
                v = (row.get(c) or "").strip()
                if v:
                    out.add(v)
    return out


def collect_p0_mother_body() -> Set[str]:
    """Campaign 頭尾 ∪ 清單對 ∪ no_natural 頭（活躍 campaign 字面）。"""
    s: Set[str] = set()
    s |= _tsv_literals(ANT_TSV, ("head", "tail"))
    s |= _tsv_literals(SYN_TSV, ("head", "tail"))
    s |= _tsv_literals(NN_ANT, ("head",))
    s |= _tsv_literals(NN_SYN, ("head",))
    for path in CAMP_HEAD_TSVS:
        s |= _tsv_literals(path, ("head",))
    return {x for x in s if x}


def freeze_p0_mother_body(path: Path = P0_BODY) -> Path:
    body = sorted(collect_p0_mother_body())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + ("\n" if body else ""), encoding="utf-8")
    return path


def load_p0_mother_body(path: Path = P0_BODY) -> List[str]:
    if not path.is_file():
        freeze_p0_mother_body(path)
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def load_cow_pos_map(path: Path = COW_MAP) -> Dict[str, List[str]]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    lits = data.get("literals") if isinstance(data, dict) else None
    if not isinstance(lits, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for lit, tags in lits.items():
        if not isinstance(tags, list):
            continue
        formal = sorted({t.lower() for t in tags if isinstance(t, str) and t.lower() in FORMAL_POS})
        # COW r = adverb; our r = 副 — same. n/v/a ok. drop unknown.
        if formal:
            out[str(lit)] = formal
    return out


_NUMERAL_CHARS = set("0123456789一二三四五六七八九十百千萬亿億兩两零〇甲乙丙丁")

# Ordinary len4 NP tails — not auto 熟語
_LEN4_N_SUFFIXES = (
    "工業", "系統", "細胞", "資料", "電影", "網絡", "網路", "成本", "醫生", "地區",
    "業務", "藝術", "措施", "模式", "水準", "水平", "元素", "粒子", "原理", "生物",
    "電話", "安全", "軍人", "劇目", "典禮", "公署", "作用", "應答", "賽跑", "公司",
    "中心", "大學", "學院", "醫院", "市場", "政府", "國家", "社會", "經濟", "文化",
    "技術", "工程", "設備", "產品", "服務", "問題", "情況", "現象", "結果", "方法",
    "主義", "分子", "機構", "組織", "部門", "單位", "人員", "人士", "專家", "學者",
)

# p1-audit: only strong resultative endings (好/上/下/來/過 caused false v on 只好/以上/原來…)
_VERBISH_SUFFIX = ("掉", "完", "住", "開")


def _looks_numeral(lit: str) -> bool:
    return bool(lit) and all(c in _NUMERAL_CHARS for c in lit)


def _looks_len4_noun(lit: str) -> bool:
    if len(lit) != 4:
        return False
    if any(lit.endswith(s) for s in _LEN4_N_SUFFIXES):
        return True
    if "之" in lit[1:3]:
        return True
    return False


def propose_for_literal(
    lit: str,
    *,
    cow: Dict[str, List[str]],
) -> Optional[Tuple[str, str, str, str, str, str]]:
    """Return (pos, family, voice, note, source, confidence) or None."""
    if lit in _HEURISTIC_POS:
        return (_HEURISTIC_POS[lit], "", "", "heuristic", "heuristic", "high")
    if _looks_numeral(lit):
        return ("x", "", "", "numeral", "heuristic", "high")
    if _looks_len4_noun(lit):
        return ("n", "", "", "len4-noun-heuristic", "heuristic", "medium")
    if lit in cow:
        tags = [t for t in cow[lit] if t in FORMAL_POS]
        if tags:
            # Single-tag COW ~13% primary error → never high
            note = "cow-single" if len(tags) == 1 else "cow-multi"
            return (",".join(tags), "", "", note, "cow", "medium")
    if len(lit) >= 2 and lit[0] in "被捱受遭":
        return ("v", "", "passive", "prefix-passive", "heuristic", "medium")
    if len(lit) == 2 and any(lit.endswith(s) for s in _VERBISH_SUFFIX):
        return ("v", "", "", "verb-suffix", "heuristic", "medium")
    return ("u", "", "", "no-source", "fallback", "low")


def build_proposals(
    body: Sequence[str],
    *,
    existing: Optional[Set[str]] = None,
    cow: Optional[Dict[str, List[str]]] = None,
) -> List[dict]:
    have = existing if existing is not None else set(parse_project_pos_tsv().keys())
    cow_map = cow if cow is not None else load_cow_pos_map()
    rows: List[dict] = []
    for lit in body:
        if lit in have:
            continue
        prop = propose_for_literal(lit, cow=cow_map)
        if not prop:
            continue
        pos, family, voice, note, source, conf = prop
        rows.append(
            {
                "literal": lit,
                "pos": pos,
                "family": family,
                "voice": voice,
                "note": note,
                "source": source,
                "confidence": conf,
            }
        )
    return rows


def write_proposals(rows: Sequence[dict], path: Path = P0_PROPOSALS) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(PROPOSAL_HEADER), delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in PROPOSAL_HEADER})
    return path


def read_proposals(path: Path) -> List[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def merge_proposals_into_ssot(
    proposals: Sequence[dict],
    *,
    tsv: Path = DEFAULT_TSV,
    only_confidence: Optional[Set[str]] = None,
    skip_undetermined: bool = False,
    dry_run: bool = False,
) -> dict:
    """Append new literals to SSOT. Never overwrite existing."""
    table = parse_project_pos_tsv(tsv)
    added = 0
    skipped = 0
    bad = 0
    new_lines: List[str] = []
    for row in proposals:
        lit = (row.get("literal") or "").strip()
        if not lit or lit in table:
            skipped += 1
            continue
        conf = (row.get("confidence") or "").strip().lower()
        if only_confidence and conf not in only_confidence:
            skipped += 1
            continue
        pos_raw = (row.get("pos") or "").strip()
        if skip_undetermined and pos_raw.replace(",", "").replace("|", "") == "u":
            skipped += 1
            continue
        try:
            pos = split_pos(pos_raw)
        except ProjectPosError:
            bad += 1
            continue
        family = (row.get("family") or "").strip()
        voice = (row.get("voice") or "").strip()
        if family not in ("", "idiom") or voice not in ("", "active", "passive"):
            bad += 1
            continue
        note = (row.get("note") or "").strip()
        src = (row.get("source") or "").strip()
        if src and src not in note:
            note = f"{note};{src}" if note else src
        pos_cell = ",".join(sorted(pos))
        new_lines.append(f"{lit}\t{pos_cell}\t{family}\t{voice}\t{note}")
        added += 1
    if not dry_run and new_lines:
        raw = tsv.read_text(encoding="utf-8")
        prefix = "" if raw.endswith("\n") else "\n"
        with tsv.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(prefix + "\n".join(new_lines) + "\n")
    return {"added": added, "skipped": skipped, "bad": bad, "dry_run": dry_run}


def p0_status(*, body_path: Path = P0_BODY, tsv: Path = DEFAULT_TSV) -> dict:
    from ingest.project_pos_lexicon_prune import load_lexicon_literals

    raw = set(load_p0_mother_body(body_path))
    try:
        lex = load_lexicon_literals()
        body = raw & lex
        out_of_lex = len(raw) - len(body)
    except FileNotFoundError:
        body = raw
        out_of_lex = 0
    table = parse_project_pos_tsv(tsv)
    from ingest.project_pos_alias import covered_literals

    covered = covered_literals(table)
    tagged = body & covered
    in_table = body & set(table.keys())
    gate_formal = {lit for lit in in_table if table[lit].gate_pos()}
    undetermined = {lit for lit in in_table if table[lit].pos <= frozenset({"u"})}
    low_draft = {
        lit
        for lit in in_table
        if table[lit].trust() == "low" and bool(table[lit].formal_pos())
    }
    missing = body - covered
    complete = len(missing) == 0 and len(body) > 0
    return {
        "mother_body": len(raw),
        "mother_in_lexicon": len(body),
        "mother_out_of_lexicon": out_of_lex,
        "tagged": len(tagged),
        "formal": len(gate_formal),
        "gate_formal": len(gate_formal),
        "low_draft_formal": len(low_draft),
        "undetermined_only": len(undetermined),
        "missing": len(missing),
        "coverage": round(len(tagged) / len(body), 4) if body else 0.0,
        "formal_coverage": round(len(gate_formal) / len(body), 4) if body else 0.0,
        "p0_complete": complete,
        "p0_hard_gate_ready": complete,
    }


def update_meta_p0(status: dict, *, meta_path: Path = DEFAULT_META, enable_hard_gate: bool = False) -> None:
    meta = load_meta(meta_path)
    meta["p0"] = {
        "mother_body": status["mother_body"],
        "tagged": status["tagged"],
        "formal": status["formal"],
        "missing": status["missing"],
        "coverage": status["coverage"],
        "formal_coverage": status["formal_coverage"],
        "complete": status["p0_complete"],
    }
    if enable_hard_gate and status["p0_complete"]:
        meta["p0_hard_gate"] = True
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_freeze(_: argparse.Namespace) -> int:
    path = freeze_p0_mother_body()
    n = len(load_p0_mother_body(path))
    print(json.dumps({"out": str(path), "literals": n}, ensure_ascii=False))
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    body = load_p0_mother_body()
    rows = build_proposals(body)
    if args.min_confidence == "high":
        rows = [r for r in rows if r["confidence"] == "high"]
    elif args.min_confidence == "medium":
        rows = [r for r in rows if r["confidence"] in ("high", "medium")]
    out = write_proposals(rows, Path(args.out) if args.out else P0_PROPOSALS)
    by = {}
    for r in rows:
        by[r["confidence"]] = by.get(r["confidence"], 0) + 1
    print(json.dumps({"out": str(out), "proposals": len(rows), "by_confidence": by}, ensure_ascii=False))
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    path = Path(args.proposals) if args.proposals else P0_PROPOSALS
    rows = read_proposals(path)
    conf: Optional[Set[str]] = None
    if args.only_confidence:
        conf = {c.strip() for c in args.only_confidence.split(",") if c.strip()}
    if args.only_source:
        allow = {s.strip() for s in args.only_source.split(",") if s.strip()}
        rows = [r for r in rows if (r.get("source") or "").strip() in allow]
    if args.only_note_prefix:
        pref = args.only_note_prefix
        rows = [r for r in rows if (r.get("note") or "").startswith(pref)]
    stats = merge_proposals_into_ssot(
        rows,
        only_confidence=conf,
        skip_undetermined=bool(args.skip_u),
        dry_run=bool(args.dry_run),
    )
    if not args.dry_run and stats["added"]:
        write_carrier()
    st = p0_status()
    update_meta_p0(st, enable_hard_gate=bool(args.enable_hard_gate))
    print(json.dumps({"merge": stats, "status": st}, ensure_ascii=False))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    if not P0_BODY.is_file():
        freeze_p0_mother_body()
    st = p0_status()
    update_meta_p0(st)
    print(json.dumps(st, ensure_ascii=False))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_p0")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze", help="freeze P0 mother body")
    pr = sub.add_parser("propose", help="write proposal TSV for untagged body")
    pr.add_argument("--out", default="")
    pr.add_argument("--min-confidence", choices=("low", "medium", "high"), default="low")
    mg = sub.add_parser("merge", help="merge proposals into SSOT")
    mg.add_argument("--proposals", default="")
    mg.add_argument("--only-confidence", default="", help="e.g. high or high,medium")
    mg.add_argument("--only-source", default="", help="e.g. heuristic,cow")
    mg.add_argument("--only-note-prefix", default="", help="e.g. cow-multi")
    mg.add_argument("--skip-u", action="store_true", help="skip pos=u rows")
    mg.add_argument("--dry-run", action="store_true")
    mg.add_argument("--enable-hard-gate", action="store_true", help="set p0_hard_gate if complete")
    sub.add_parser("status", help="P0 coverage report")
    args = p.parse_args(argv)
    if args.cmd == "freeze":
        return cmd_freeze(args)
    if args.cmd == "propose":
        return cmd_propose(args)
    if args.cmd == "merge":
        return cmd_merge(args)
    if args.cmd == "status":
        return cmd_status(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
