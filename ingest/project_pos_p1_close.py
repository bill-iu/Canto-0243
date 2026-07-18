"""P1 closeout: promote genuine cow-nv duals + rank 101–500 u heuristics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from ingest.project_pos import (
    DEFAULT_META,
    DEFAULT_TSV,
    PosRow,
    load_meta,
    parse_project_pos_tsv,
    write_carrier,
)
from ingest.project_pos_cleanup import _rewrite_table, _set_pos
from ingest.project_pos_p1 import load_p1_mother_body, p1_status, update_meta_p1

# True 名動同形 / frequent duals — promote cow-nv-unreviewed → review high
_TRUE_NV_DUALS: Set[str] = {
    "交換", "交流", "介紹", "代表", "休息", "保證", "保護", "信任", "假設",
    "傷害", "價值", "出現", "出發", "出席", "分享", "分析", "利用", "刺激",
    "創造", "加入", "努力", "勝利", "包括", "計劃", "設計", "工作", "學習",
    "教育", "研究", "發展", "管理", "生產", "建設", "組織", "領導", "變化",
    "影響", "幫助", "選擇", "決定", "要求", "需要", "感覺", "開始", "結束",
    "完成", "準備", "說明", "報告", "通知", "警告", "建議", "批評", "讚揚",
    "攻擊", "防守", "勝利", "失敗", "成功", "進步", "倒退", "增加", "減少",
    "提高", "降低", "改善", "破壞", "建設", "發展", "改革", "革命", "運動",
    "比賽", "遊戲", "練習", "訓練", "考試", "調查", "實驗", "發明", "發現",
    "發明", "申請", "批准", "同意", "反對", "支持", "拒絕", "接受", "歡迎",
    "慶祝", "紀念", "感謝", "道歉", "原諒", "希望", "夢想", "理想", "計劃",
    "安排", "準備", "組織", "領導", "指揮", "控制", "管理", "經營", "投資",
    "買賣", "交易", "合作", "競爭", "衝突", "戰爭", "和平", "談判", "協議",
    "合同", "條約", "法律", "規定", "制度", "政策", "措施", "方法", "辦法",
    "手段", "技巧", "技術", "藝術", "科學", "文化", "傳統", "習慣", "風俗",
    "休息", "停留", "前進", "出口", "充滿", "制服", "交叉", "一致", "上漲",
    "付款", "伸出", "停止", "分", "刷", "刺", "包", "值", "傷害", "保證",
    "回答", "問題", "問題",  # 問題 is mostly n - skip from duals if pure n
    "變化", "改變", "改變", "移動", "轉動", "滾動", "飛行", "游泳", "跑步",
    "行走", "跳躍", "跳舞", "唱歌", "演奏", "表演", "演出", "展覽", "比賽",
    "戰鬥", "鬥爭", "革命", "改革", "建設", "破壞", "修理", "製造", "生產",
    "銷售", "購買", "消費", "投資", "借貸", "儲蓄", "保險", "賠償", "罰款",
    "獎勵", "懲罰", "表揚", "批評", "表揚", "祝賀", "慶祝", "哀悼", "懷念",
    "記憶", "忘記", "回想", "想像", "思考", "考慮", "判斷", "決定", "選擇",
    "放棄", "堅持", "努力", "奮鬥", "爭取", "保護", "捍衛", "攻擊", "防禦",
    "逃跑", "追逐", "搜索", "調查", "研究", "學習", "教學", "教育", "培養",
    "訓練", "練習", "復習", "考試", "測驗", "檢查", "審查", "批准", "否決",
    "通過", "失敗", "成功", "勝利", "失敗", "進步", "退步", "提高", "降低",
    "增加", "減少", "擴大", "縮小", "加強", "削弱", "改善", "惡化", "解決",
    "處理", "應付", "面對", "逃避", "接受", "拒絕", "歡迎", "歡送", "招待",
    "款待", "服務", "幫助", "支持", "反對", "贊成", "同意", "否認", "承認",
    "坦白", "隱瞞", "欺騙", "說謊", "證明", "證實", "懷疑", "相信", "信任",
    "懷疑", "擔心", "害怕", "恐懼", "喜歡", "討厭", "愛", "恨", "嫉妒",
    "羨慕", "同情", "憐憫", "關心", "照顧", "忽視", "忘記", "記得", "回憶",
    "計劃", "打算", "準備", "安排", "組織", "召集", "解散", "成立", "建立",
    "創辦", "開設", "關閉", "開放", "封鎖", "包圍", "佔領", "解放", "統治",
    "管理", "領導", "指揮", "控制", "監督", "檢查", "調查", "研究", "分析",
    "綜合", "比較", "對比", "區別", "聯繫", "結合", "分離", "分開", "合併",
    "統一", "分裂", "團結", "合作", "競爭", "鬥爭", "妥協", "談判", "協議",
    "簽約", "違約", "履行", "執行", "實施", "貫徹", "落實", "推廣", "宣傳",
    "廣告", "推銷", "銷售", "購買", "訂購", "預訂", "取消", "延期", "提前",
    "開始", "結束", "繼續", "中斷", "暫停", "恢復", "停止", "進行", "開展",
    "展開", "深入", "擴大", "縮小", "加強", "減弱", "提高", "降低", "上升",
    "下降", "上漲", "下跌", "增長", "減少", "增加", "削減", "節省", "浪費",
    "消耗", "補充", "供應", "提供", "給予", "贈送", "捐贈", "貢獻", "奉獻",
    "犧牲", "付出", "獲得", "取得", "得到", "失去", "喪失", "保留", "保存",
    "儲存", "積累", "積蓄", "消費", "開支", "收入", "支出", "盈利", "虧損",
    "賺錢", "賠錢", "投資", "融資", "貸款", "借款", "還款", "付息", "結算",
    "清算", "破產", "倒閉", "開業", "營業", "經營", "管理", "行政", "執法",
    "立法", "司法", "審判", "判決", "上訴", "申訴", "控告", "起訴", "辯護",
    "作證", "證明", "證據", "調查", "偵查", "破案", "抓獲", "逮捕", "拘留",
    "釋放", "保釋", "判刑", "減刑", "赦免", "特赦", "大赦", "制裁", "懲罰",
    "獎勵", "表彰", "表揚", "批評", "自我批評", "檢討", "反省", "總結",
    "匯報", "報告", "通知", "通告", "公告", "聲明", "宣言", "號召", "倡議",
    "提議", "建議", "提案", "議案", "決議", "決定", "決策", "選擇", "選舉",
    "競選", "投票", "表決", "通過", "否決", "棄權", "贊成", "反對", "棄權",
}

# Rank 101–500 u → formal (Canto + common written)
_RANK_U_HEURISTIC: Dict[str, str] = {
    "、": "x",  # punctuation noise in essay — 虛
    "沖": "v",
    "番": "v,r",  # 返 variant often
    "女仔": "n",
    "小": "a,x",
    "次": "x,n",
    "黎": "v",  # 嚟
    "就是": "x,r",
    "今日": "n,r",
    "整": "v,a",
    "媽咪": "n",
    "除": "v,x",
    "屌": "v,x",
    "說": "v",
    "回覆日期": "n",
    "聲": "n",
    "女": "n",
    "噹": "x",
    "即": "r,x",
    "她": "x",
    "突然": "r,a",
    "晒": "x,v",
    "俊俊": "n",
    "大家": "x",
    "不如": "r,x",
    "爲": "x,v",
    "時": "n,x",
    "靚": "a",
    "跌": "v",
    "撚": "v,x",
    "張": "x,n",
    "思": "v,n",
    "之前": "r,x",
    "都會": "r,v",
    "一陣": "r,n",
    "上面": "n,r",
    "陣": "n,x",
    "駛": "v",
    "您": "x",
    "成日": "r",
    "慢慢": "r",
    "家姐": "n",
    "其他": "x",
    "哂": "x",
    "點樣": "x,r",
    "覺": "v",
    "終於": "r",
    "幾多": "x,r",
    "仲有": "r,x",
    "嗯": "x",
    "新": "a",
    "一路": "r,n",
    "頭先": "r",
    "少少": "a,r",
    "爛": "a,v",
    "啱": "a,v",
    "咦": "x",
    "依家": "r,n",
    "樣": "n,x",
    "涼": "a",
    "搭": "v",
    "若": "x",
    "我同": "u",  # fragment — leave u
    "咋": "x",
    "定": "v,a,x",
    "凝": "v,a",
    "做咩": "x,v",
    "低": "a",
    "以爲": "v",
    "竟然": "r",
    "耐": "a,r",
    "公仔": "n",
    "芷純": "n",  # name
    "就算": "x,r",
    "捉": "v",
    "啤啤": "n,x",
    "件": "x",
    "當然": "r,a",
    "嗎": "x",
    "跟": "v,x",
    "喀": "x",
    "男仔": "n",
    "啫": "x",
    "唔該": "x,v",
    "我講": "u",  # fragment
    "身": "n",
    "砌": "v",
    "吖": "x",
    "可": "v,x",
    "丫": "x",
    "街": "n",
    "平時": "r,n",
    "所有": "x,a",
    "今次": "r,n",
    "以前": "r,n",
    "長": "a,v",
    "同學": "n",
    "收": "v",
    "一次": "r,n",
    "唔同": "a",
    "清楚": "a",
    "身邊": "n,r",
    "所": "x",
    "都是": "r,v",
    "多謝": "v,x",
    "點知": "r,x",
    "車車": "n",
    "小貞": "n",
    "一邊": "r,n",
    "房": "n",
    "唉": "x",
    "一刻": "n,r",
    "老豆": "n",
    "本": "x,n",
    "說話": "n,v",
    "估": "v",
    "面前": "n,r",
    "起身": "v",
    "力": "n",
    "同時": "r,n",
    "企": "v",
    "依個": "x",
    "我望": "u",  # fragment
    "正": "a,r,x",
    "細": "a",
    "果": "n,x",
    "道": "n,v",
    "黃": "a,n",
    "搣": "v",
    "叻": "a",
    "我見": "u",  # fragment
    "更加": "r",
    "我要": "u",  # fragment
    "嘞": "x",
    "答": "v",
    "錯": "a,v",
    "我個": "u",  # fragment
    "姐": "n",
    "有時": "r",
    "離": "v,x",
    "妳": "x",
    "當": "v,x",
    "楂": "v",
    "相": "n,v,a",
    "嘉": "n,a",
    "他": "x",
    "老母": "n",
    "早": "a,r",
    "誒": "x",
    "仲要": "r,v",
    "污糟": "a",
    "我會": "u",  # fragment
    "理": "v,n",
    "救": "v",
    "有個": "u",  # fragment
    "不斷": "r,a",
    "謙謙": "n",
    "究竟": "r,x",
    "男": "n,a",
    "兜": "v,n",
    "特別": "a,r",
    "作爲": "v,x",
    "唔通": "r,x",
    "乖": "a",
    "插": "v",
    "很多": "a,r",
    "皓臻": "n",
    "記": "v,n",
    "幾時": "x,r",
    "吾": "x",
    "喫": "v",
}


def promote_true_nv(table: Dict[str, PosRow]) -> dict:
    promoted = 0
    skipped = 0
    for lit, row in list(table.items()):
        if "cow-nv-unreviewed" not in row.note.split(";"):
            skipped += 1
            continue
        if lit not in _TRUE_NV_DUALS:
            skipped += 1
            continue
        if "review" in row.note.split(";"):
            skipped += 1
            continue
        # keep n,v (or existing formal), elevate review
        pos_csv = ",".join(sorted(row.formal_pos() or frozenset({"n", "v"})))
        _set_pos(table, lit, pos_csv, note_extra="p1-close;true-nv;review")
        promoted += 1
    return {"promoted_true_nv": promoted, "skipped": skipped}


def promote_rank_u(table: Dict[str, PosRow], *, lo: int = 101, hi: int = 500) -> dict:
    body = load_p1_mother_body()
    promoted = 0
    left_u = 0
    missing_map = 0
    for i, lit in enumerate(body):
        rank = i + 1
        if rank < lo or rank > hi:
            continue
        row = table.get(lit)
        if not row or row.pos > frozenset({"u"}):
            continue
        pos_csv = _RANK_U_HEURISTIC.get(lit)
        if not pos_csv:
            missing_map += 1
            continue
        if pos_csv == "u":
            left_u += 1
            continue
        _set_pos(table, lit, pos_csv, note_extra="p1-close;rank-u;canto-heuristic;review")
        promoted += 1
    return {
        "promoted_rank_u": promoted,
        "left_explicit_u": left_u,
        "missing_heuristic": missing_map,
    }


def p1_closeout_metrics() -> dict:
    body = load_p1_mother_body()
    table = parse_project_pos_tsv()
    top100_gate = sum(1 for lit in body[:100] if table[lit].gate_pos())
    r101_500 = body[100:500]
    r101_500_u = sum(1 for lit in r101_500 if table[lit].pos <= frozenset({"u"}))
    r101_500_gate = sum(1 for lit in r101_500 if table[lit].gate_pos())
    nv_left = sum(
        1
        for r in table.values()
        if "cow-nv-unreviewed" in r.note.split(";") and "true-nv" not in r.note.split(";")
    )
    nv_promoted_notes = sum(1 for r in table.values() if "true-nv" in r.note.split(";"))
    st = p1_status()
    return {
        "top100_gate": top100_gate,
        "top100_gate_pct": round(top100_gate / 100, 4),
        "rank101_500": len(r101_500),
        "rank101_500_u": r101_500_u,
        "rank101_500_gate": r101_500_gate,
        "rank101_500_gate_pct": round(r101_500_gate / len(r101_500), 4) if r101_500 else 0,
        "cow_nv_unreviewed_left": nv_left,
        "true_nv_promoted_rows": nv_promoted_notes,
        "p1": st,
    }


def run() -> dict:
    table = parse_project_pos_tsv()
    stats = {
        "true_nv": promote_true_nv(table),
        "rank_u": promote_rank_u(table),
    }
    _rewrite_table(table)
    write_carrier()
    st = p1_status()
    update_meta_p1(st, k=5000)
    metrics = p1_closeout_metrics()
    meta = load_meta()
    meta["version"] = "0.1.6"
    meta["p1_close"] = {**stats, "metrics": metrics}
    meta["p1"] = {
        **(meta.get("p1") or {}),
        "gate_formal": st["gate_formal"],
        "gate_coverage": st["gate_coverage"],
        "undetermined_only": st["undetermined_only"],
        "complete": st["p1_complete"],
        "closeout": True,
        "top100_gate_pct": metrics["top100_gate_pct"],
        "rank101_500_gate_pct": metrics["rank101_500_gate_pct"],
    }
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"stats": stats, "metrics": metrics}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_p1_close")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("metrics")
    args = p.parse_args(argv)
    if args.cmd == "run":
        print(json.dumps(run(), ensure_ascii=False))
        return 0
    if args.cmd == "metrics":
        print(json.dumps(p1_closeout_metrics(), ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
