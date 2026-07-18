"""G1 audit for nf2k_gate_r1.tsv."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from ingest.project_pos_audit import apply_verdicts_file, upsert_ssot_rows
from ingest.project_pos import write_carrier

DIR = Path(__file__).resolve().parent
PATH = DIR / "nf2k_gate_r1.tsv"

# Most OK; few BAD/SOFT
VERDICTS: dict[str, tuple[str, str, str]] = {
    "三個字": ("SOFT", "", "數量短語；n 主，x 弱可留"),
    "不由": ("OK", "", ""),
    "中標": ("OK", "", ""),
    "主題曲": ("OK", "", ""),
    "二手車": ("OK", "", ""),
    "交投": ("OK", "", ""),
    "作案": ("OK", "", ""),
    "侃": ("OK", "", ""),
    "僅供參考": ("BAD", "x", "套語／標記，非動詞；清 family 另修"),
    "儒": ("OK", "", ""),
    "光管": ("OK", "", ""),
    "全都": ("OK", "", ""),
    "公安部": ("OK", "", ""),
    "冥": ("OK", "", ""),
    "利申": ("OK", "", ""),
    "卑": ("OK", "", ""),
    "原廠": ("OK", "", ""),
    "反口": ("OK", "", ""),
    "吞噬": ("OK", "", ""),
    "唸書": ("OK", "", ""),
    "商貿": ("OK", "", ""),
    "域": ("OK", "", ""),
    "埲": ("OK", "", ""),
    "壞人": ("OK", "", ""),
    "大自然": ("OK", "", ""),
    "奉上": ("OK", "", ""),
    "姦": ("OK", "", ""),
    "客商": ("OK", "", ""),
    "實戰": ("SOFT", "", "n 主；亦 v"),
    "小米": ("OK", "", ""),
    "嵌": ("OK", "", ""),
    "帶眼": ("OK", "", ""),
    "幫派": ("OK", "", ""),
    "建國": ("OK", "", ""),
    "強逼": ("OK", "", ""),
    "彩鈴": ("OK", "", ""),
    "循例": ("OK", "", ""),
    "恕": ("OK", "", ""),
    "感觸": ("OK", "", ""),
    "慢吞吞": ("OK", "", ""),
    "成員國": ("OK", "", ""),
    "技術含量": ("OK", "", ""),
    "抽空": ("OK", "", ""),
    "擴容": ("OK", "", ""),
    "整爛": ("OK", "", ""),
    "文科": ("OK", "", ""),
    "時勢": ("OK", "", ""),
    "暗地": ("OK", "", ""),
    "暗自": ("OK", "", ""),
    "有期徒刑": ("OK", "", ""),
    "概況": ("OK", "", ""),
    "樓房": ("OK", "", ""),
    "歡": ("OK", "", ""),
    "沁": ("OK", "", ""),
    "沉迷": ("OK", "", ""),
    "測繪": ("OK", "", ""),
    "無意中": ("OK", "", ""),
    "焦": ("OK", "", ""),
    "煞": ("BAD", "a,v", "四標過寬；煞車／兇煞分義收 a,v"),
    "瑜伽": ("OK", "", ""),
    "環境污染": ("OK", "", ""),
    "由來": ("OK", "", ""),
    "當着": ("OK", "", ""),
    "瘦身": ("OK", "", ""),
    "真誠": ("OK", "", ""),
    "禹": ("OK", "", ""),
    "科普": ("OK", "", ""),
    "竈頭": ("OK", "", ""),
    "笑死": ("OK", "", ""),
    "管理費": ("OK", "", ""),
    "築": ("OK", "", ""),
    "米飯": ("OK", "", ""),
    "粒聲": ("OK", "", ""),
    "素養": ("OK", "", ""),
    "經已": ("OK", "", ""),
    "網格": ("OK", "", ""),
    "耳筒": ("OK", "", ""),
    "耶": ("OK", "", ""),
    "耶和華": ("OK", "", ""),
    "聊天": ("OK", "", ""),
    "胸肌": ("OK", "", ""),
    "荷花": ("OK", "", ""),
    "葵涌": ("OK", "", ""),
    "蔥": ("OK", "", ""),
    "視圖": ("OK", "", ""),
    "評議": ("OK", "", ""),
    "警覺": ("OK", "", ""),
    "豐富多彩": ("OK", "", ""),
    "貫穿": ("OK", "", ""),
    "費時": ("OK", "", ""),
    "起上嚟": ("OK", "", ""),
    "車子": ("OK", "", ""),
    "軍區": ("OK", "", ""),
    "轉速": ("OK", "", ""),
    "連帶": ("OK", "", ""),
    "雙面": ("OK", "", ""),
    "飛碟": ("OK", "", ""),
    "高產": ("OK", "", ""),
    "鬥地主": ("OK", "", ""),
    "點好": ("OK", "", ""),
}


def main() -> None:
    rows = list(csv.DictReader(PATH.open(encoding="utf-8"), delimiter="\t"))
    c = Counter()
    out = []
    for r in rows:
        lit = r["literal"]
        v, fp, note = VERDICTS[lit]
        r["verdict"] = v
        r["fix_pos"] = fp
        r["audit_note"] = note
        c[v] += 1
        out.append(r)
    n = sum(c.values())
    rate = (c["OK"] + c["SOFT"]) / n
    print(dict(c), "ok_rate", round(rate, 4), "PASS" if rate >= 0.90 else "FAIL")
    with PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    res = apply_verdicts_file(PATH, dry_run=False)
    print("apply", res)
    # clear idiom on 僅供參考
    up = upsert_ssot_rows(
        [
            {
                "literal": "僅供參考",
                "fix_pos": "x",
                "fix_family": "",
                "fix_voice": "",
                "note": "套語",
                "audit_note": "nf2k-gate",
            }
        ],
        note_suffix="u-inlex-nf2k",
    )
    write_carrier()
    print("僅供參考 clear family", up)

    # tag keep-u as fragments
    keep = [
        ("我溝", "clause-slice", "主+動截斷"),
        ("將你", "clause-slice", "介+代截斷"),
        ("實會", "clause-slice", "實+會截斷"),
        ("自已", "clause-slice", "自己誤寫／殘片"),
        ("關斗", "opaque", "罕／不明"),
        ("拉西", "opaque", "罕／不明"),
        ("牴", "residual", "牴觸殘字 — 待完整詞 alias"),
        ("魍", "residual", "魍魎殘字 — 待完整詞 alias"),
    ]
    from ingest.project_pos import parse_project_pos_tsv, PosRow
    from ingest.project_pos_cleanup import _rewrite_table
    from ingest.project_pos_alias import _with_tokens

    table = parse_project_pos_tsv()
    for lit, kind, note in keep:
        row = table.get(lit)
        if not row:
            continue
        table[lit] = PosRow(
            lit,
            frozenset({"u"}),
            row.family,
            row.voice,
            _with_tokens(row.note, "fragment", kind, note),
        )
    _rewrite_table(table)
    write_carrier()
    print("tagged keep-u fragments", len(keep))


if __name__ == "__main__":
    main()
