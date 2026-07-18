import csv
from collections import Counter
from pathlib import Path

from ingest.project_pos_audit import apply_verdicts_file

verdicts = {
    "一心一意": ("OK", "", ""),
    "一房一廳": ("OK", "", ""),
    "一手一足": ("OK", "", ""),
    "一時三刻": ("OK", "", ""),
    "一望無垠": ("OK", "", ""),
    "一驚一乍": ("OK", "", ""),
    "一點一滴": ("OK", "", ""),
    "亦莊亦諧": ("OK", "", ""),
    "人無完人": ("OK", "", ""),
    "仁者見仁": ("OK", "", ""),
    "倒買倒賣": ("SOFT", "", "v 主；a 弱"),
    "做牛做馬": ("SOFT", "", "v 主"),
    "傾國傾城": ("SOFT", "", "a 主形容容貌"),
    "像模像樣": ("SOFT", "", "a 主"),
    "全始全終": ("BAD", "r", "自始至終義；副詞性"),
    "可有可無": ("SOFT", "", "a 主"),
    "各就各位": ("BAD", "v", "祈使/動作；非 a"),
    "各色各樣": ("OK", "", ""),
    "同班同學": ("OK", "", "非熟語；family 空正確"),
    "多彩多姿": ("OK", "", ""),
    "大吃大喝": ("OK", "", ""),
    "大徹大悟": ("OK", "", ""),
    "夾手夾腳": ("OK", "", ""),
    "學士學位": ("OK", "", "非熟語 n"),
    "屢戰屢敗": ("OK", "", ""),
    "屢敗屢戰": ("OK", "", ""),
    "後知後覺": ("OK", "", ""),
    "成千成萬": ("OK", "", ""),
    "挨門挨户": ("OK", "", ""),
    "探頭探腦": ("SOFT", "", "a 可；亦 v"),
    "敢作敢為": ("OK", "", ""),
    "敢作敢當": ("OK", "", ""),
    "新人新事": ("OK", "", ""),
    "旅進旅退": ("OK", "", ""),
    "日復一日": ("OK", "", ""),
    "時大時小": ("OK", "", ""),
    "時斷時續": ("OK", "", ""),
    "沒日沒夜": ("SOFT", "", "a,r 亦可"),
    "活學活用": ("OK", "", ""),
    "滑頭滑腦": ("OK", "", ""),
    "腳痛醫腳": ("OK", "", ""),
    "自動自發": ("OK", "", ""),
    "至始至終": ("OK", "", ""),
    "親力親為": ("OK", "", ""),
    "賊頭賊腦": ("OK", "", ""),
    "逐字逐句": ("BAD", "r", "方式副；非 a,v"),
    "雙宿雙飛": ("OK", "", ""),
    "電子電路": ("OK", "", "術語 n；非熟語"),
    "風言風語": ("BAD", "n", "閒話名詞；非 a,v"),
    "鬥智鬥力": ("OK", "", ""),
}

path = Path("data/pos/audit/u_inlex/u_inlex_idiom_gate_r1.tsv")
rows = list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))
c = Counter()
out = []
for r in rows:
    lit = r["literal"]
    v, fp, note = verdicts[lit]
    r["verdict"] = v
    r["fix_pos"] = fp
    r["audit_note"] = note
    c[v] += 1
    out.append(r)
n = sum(c.values())
rate = (c["OK"] + c["SOFT"]) / n
print(dict(c), "ok_rate", round(rate, 4), "PASS" if rate >= 0.90 else "FAIL")
with path.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(out)
print(apply_verdicts_file(path, dry_run=False))
