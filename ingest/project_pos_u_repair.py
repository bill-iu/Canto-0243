"""Repair mass pos=u under-tags: AABB / 有無對 / 之字格 / 粵語高頻啓發式."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from ingest.project_pos import DEFAULT_META, PosRow, load_meta, parse_project_pos_tsv, write_carrier
from ingest.project_pos_cleanup import _rewrite_table
from ingest.project_pos_p1 import load_essay_ranked

# High-freq / Canto under-tags (pos_csv). Explicit "u" omitted = leave undetermined.
_CANTO_U_MAP: Dict[str, str] = {
    "男朋友": "n",
    "女朋友": "n",
    "老公": "n",
    "老婆": "n",
    "老豆": "n",
    "老母": "n",
    "阿媽": "n",
    "阿爸": "n",
    "細佬": "n",
    "家姐": "n",
    "細路": "n",
    "小朋友": "n",
    "屋企": "n",
    "越": "r,v",
    "嬲": "v,a",
    "明": "a,v",
    "約": "v,n",
    "之間": "x,n",
    "淨係": "r,x",
    "攬": "v",
    "位": "x,n",
    "也是": "r,v",
    "傻": "a",
    "吧": "x",
    "粒": "x",
    "着": "v,x",
    "妖": "n,a",
    "唔使": "v,x",
    "傾": "v",
    "噉樣": "r,x",
    "咁樣": "r,x",
    "好彩": "a,r",
    "香": "a,n",
    "聽日": "n,r",
    "尋日": "n,r",
    "琴日": "n,r",
    "呃": "v,x",
    "不停": "r,a",
    "啱啱": "r",
    "明明": "r",
    "梳": "v,n",
    "仍然": "r",
    "回應": "v,n",
    "唔記得": "v",
    "記得": "v",
    "攰": "a",
    "肚餓": "a",
    "口渴": "a",
    "靚仔": "n,a",
    "靚女": "n,a",
    "差唔多": "a,r",
    "差不多": "a,r",
    "好多": "a,r",
    "好少": "a,r",
    "搞掂": "v",
    "搞錯": "v",
    "傾偈": "v",
    "傾計": "v",
    "食飯": "v",
    "瞓覺": "v",
    "返屋企": "v",
    "出街": "v",
    "返工": "v",
    "放工": "v",
    "放假": "v",
    "收工": "v",
    "開工": "v",
    "睇戲": "v",
    "打機": "v",
    "打電話": "v",
    "人哋": "x",
    "而家": "r,n",
    "依家": "r,n",
    "點解": "x,r",
    "點樣": "x,r",
    "邊度": "x",
    "邊個": "x",
    "幾時": "x,r",
    "幾多": "x,r",
    "咩事": "n,x",
    "唔該晒": "x",
    "多謝晒": "x,v",
    "對唔住": "x,v",
    "冇問題": "x,a",
    "冇錯": "a,x",
    "亦都": "r,x",
    "先至": "r,x",
    "即刻": "r",
    "馬上": "r",
    "立刻": "r",
    "突然": "r,a",
    "忽然": "r",
    "原來": "r",
    "其實": "r",
    "當然": "r,a",
    "一定": "r,a",
    "可能": "a,r",
    "應該": "v,x",
    "或者": "x",
    "還是": "x,r",
    "如果": "x",
    "因為": "x",
    "因爲": "x",
    "所以": "x",
    "然後": "r,x",
    "之後": "r,x",
    "之前": "r,x",
    "但係": "x",
    "不過": "r,x",
    "同埋": "x",
    "一樣": "a,r",
    "唔同": "a",
    "不同": "a",
    "清楚": "a",
    "鍾意": "v",
    "中意": "v",
    "開心": "a",
    "高興": "a",
    "快樂": "a",
    "靚": "a",
    "叻": "a",
    "乖": "a",
    "瞓": "v",
    "睇": "v",
    "諗": "v",
    "識": "v",
    "識得": "v",
    "知": "v",
    "講": "v",
    "食": "v",
    "飲": "v",
    "行": "v,n",
    "企": "v",
    "坐": "v",
    "走": "v",
    "返": "v",
    "嚟": "v",
    "去": "v",
    "做": "v",
    "玩": "v",
    "幫": "v",
    "愛": "v,n",
    "恨": "v",
    "怕": "v",
    "驚": "v,a",
    "想": "v",
    "要": "v,x",
    "會": "v,x",
    "能": "v,x",
    "得": "v,x",
    "係": "v,x",
    "是": "v,x",
    "有": "v",
    "冇": "v,x",
    "無": "v,a,x",
    "不": "r,x",
    "唔": "r,x",
    "也": "r,x",
    "都": "r,x",
    "又": "r,x",
    "再": "r",
    "就": "r,x,v",
    "先": "r,x",
    "仲": "r,x",
    "還": "r,x",
    "亦": "r,x",
    "最": "r",
    "太": "r",
    "更": "r",
    "好": "a,r",
    "幾": "r,x",
    "咁": "r,x",
    "噉": "r,x",
    "啦": "x",
    "喇": "x",
    "呀": "x",
    "啊": "x",
    "喎": "x",
    "㗎": "x",
    "啫": "x",
    "咋": "x",
    "囉": "x",
    "嘅": "x",
    "咗": "x",
    "緊": "x,a",
    "吓": "x",
    "晒": "x,v",
    "哂": "x",
    "喺": "x",
    "同": "x,v",
    "和": "x",
    "與": "x",
    "但": "x",
    "的": "x",
    "了": "x",
    "着": "v,x",
    "住": "v,x",
    "埋": "v,x",
    "翻": "v",
    "自己": "x",
    "大家": "x",
    "什麼": "x",
    "怎麼": "x,r",
    "怎樣": "x,r",
    "誰": "x",
    "哪": "x",
    "多少": "x,r",
    "仍然": "r",
    "已經": "r",
    "非常": "r",
    "十分": "r",
    "比較": "r,v",
    "需要": "v,n",
    "可以": "v,x",
    "學校": "n",
    "公司": "n",
    "朋友": "n",
    "家人": "n",
    "事情": "n",
    "問題": "n",
    "時間": "n",
    "地方": "n",
    "東西": "n",
    "工作": "n,v",
    "生活": "n,v",
    "世界": "n",
    "中國": "n",
    "香港": "n",
    "日本": "n",
    "美國": "n",
    "今天": "n,r",
    "明天": "n,r",
    "昨天": "n,r",
    "現在": "r,n",
    "以前": "r,n",
    "以後": "r,n",
    "時候": "n",
    "地方": "n",
    "時候": "n",
}


def _aabb_pos(lit: str) -> Optional[str]:
    if len(lit) != 4:
        return None
    if lit[0] == lit[1] == lit[2] == lit[3]:
        return "x"  # 哈哈哈哈
    if lit[0] == lit[1] and lit[2] == lit[3] and lit[0] != lit[2]:
        return "a"  # 含含糊糊
    return None


def _youwu_pos(lit: str) -> Optional[str]:
    if len(lit) != 4:
        return None
    if lit[0] in "有無" and lit[2] in "有無不":
        return "a"
    if lit[0] == "不" and lit[2] == "不":
        return "a,v"
    return None


def propose_u_fix(lit: str) -> Optional[Tuple[str, str]]:
    """Return (pos_csv, tag) or None to leave u."""
    if lit in _CANTO_U_MAP:
        return _CANTO_U_MAP[lit], "canto-u-map"
    aabb = _aabb_pos(lit)
    if aabb:
        return aabb, "aabb-u"
    yw = _youwu_pos(lit)
    if yw:
        return yw, "youwu-u"
    if len(lit) == 4 and "之" in lit:
        if lit.endswith(("之間", "之下", "之外")):
            return "r", "zhi-u-r"
        if lit.endswith(("之軀", "之勢", "之馬", "之地", "之士", "之寶", "之音", "之見", "之別", "之力", "之氣")):
            return "n", "zhi-u-n"
        # only if looks like idiom pattern-ish; avoid random 4-char with 之
        if lit[1] == "之" or lit[2] == "之":
            return "v", "zhi-u-v"
    if len(lit) == 4 and lit[0] == lit[1] and lit[2] != lit[3]:
        return "a,r", "aabc-u"
    return None


def repair_all_u(*, dry_run: bool = False) -> dict:
    table = parse_project_pos_tsv()
    u_lits = [lit for lit, r in table.items() if r.pos <= frozenset({"u"})]
    by_tag: Counter = Counter()
    applied = 0
    for lit in u_lits:
        prop = propose_u_fix(lit)
        if not prop:
            continue
        pos_csv, tag = prop
        by_tag[tag] += 1
        applied += 1
        if dry_run:
            continue
        row = table[lit]
        parts = [p.strip() for p in pos_csv.replace("|", ",").split(",") if p.strip()]
        note = row.note
        have = {x.strip() for x in note.split(";") if x.strip()}
        for bit in (f"u-repair:{tag}", "review"):
            if bit not in have:
                note = f"{note};{bit}" if note else bit
                have.add(bit)
        table[lit] = PosRow(
            literal=lit,
            pos=frozenset(parts),
            family=row.family,
            voice=row.voice,
            note=note,
        )
    if not dry_run and applied:
        _rewrite_table(table)
        write_carrier()
    left = (
        sum(1 for r in parse_project_pos_tsv().values() if r.pos <= frozenset({"u"}))
        if not dry_run
        else len(u_lits) - applied
    )
    return {
        "u_before": len(u_lits),
        "repaired": applied,
        "left_u": left,
        "by_tag": dict(by_tag),
        "dry_run": dry_run,
        "repair_rate": round(applied / len(u_lits), 4) if u_lits else 0.0,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_u_repair")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dry-run")
    sub.add_parser("run")
    args = p.parse_args(argv)
    if args.cmd == "dry-run":
        print(json.dumps(repair_all_u(dry_run=True), ensure_ascii=False))
        return 0
    if args.cmd == "run":
        stats = repair_all_u(dry_run=False)
        meta = load_meta()
        meta["version"] = "0.3.3"
        meta["u_repair"] = stats
        DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(stats, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
