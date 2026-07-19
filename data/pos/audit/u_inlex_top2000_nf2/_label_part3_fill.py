# one-shot fill for label_part3.tsv — not part of runtime pipeline
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

DIR = Path(__file__).resolve().parent
TSV = DIR / "label_part3.tsv"
SUMMARY = DIR / "label_part3_summary.md"

# literal -> (pos, family, note)  family ''|'idiom'; note only for u/borderline
# multi tags alpha-sorted: a,n,r,v,x
L: dict[str, tuple[str, str, str]] = {
    "西班牙語": ("n", "", ""),
    "本分": ("a,n", "", ""),
    "興致勃勃": ("a", "idiom", ""),
    "善解人意": ("a", "idiom", ""),
    "工程設計": ("n", "", ""),
    "中央銀行": ("n", "", ""),
    "旭日": ("n", "", ""),
    "觸目驚心": ("a", "idiom", ""),
    "不屑一顧": ("a,v", "idiom", ""),
    "激化": ("n,v", "", ""),
    "莎士比亞": ("n", "", ""),
    "紅顏知己": ("n", "", ""),
    "恐怖襲擊": ("n", "", ""),
    "現場直播": ("n,v", "", ""),
    "核心價值": ("n", "", ""),
    "自古以來": ("r", "", ""),
    "不亦樂乎": ("a,r", "idiom", ""),
    "往昔": ("n,r", "", ""),
    "文件格式": ("n", "", ""),
    "無線上網": ("n,v", "", ""),
    "伊斯蘭教": ("n", "", ""),
    "勞模": ("n", "", ""),
    "貨到付款": ("n,v", "", ""),
    "硬着頭皮": ("v", "idiom", ""),
    "難以想象": ("a,v", "", ""),
    "生活條件": ("n", "", ""),
    "力所能及": ("a", "idiom", ""),
    "可見一斑": ("v", "idiom", ""),
    "四面八方": ("n,r", "idiom", ""),
    "教育改革": ("n", "", ""),
    "海闊天空": ("a,n", "idiom", ""),
    "國防部長": ("n", "", ""),
    "獨資": ("a,n", "", ""),
    "聯席會議": ("n", "", ""),
    "憨厚": ("a", "", ""),
    "黑髮": ("n", "", ""),
    "一本正經": ("a", "idiom", ""),
    "國際足聯": ("n", "", ""),
    "斷層": ("n", "", ""),
    "此起彼伏": ("a,v", "idiom", ""),
    "爆米花": ("n", "", ""),
    "停車位": ("n", "", ""),
    "投資組合": ("n", "", ""),
    "應運而生": ("v", "idiom", ""),
    "上任": ("v", "", ""),
    "主力": ("n", "", ""),
    "何時": ("r,x", "", ""),
    "公關": ("n,v", "", ""),
    "出國": ("v", "", ""),
    "大吉利是": ("x", "", "粵語口彩／避諱套語"),
    "大有": ("a,v", "", ""),
    "嬌小": ("a", "", ""),
    "小聲": ("a,n,r", "", ""),
    "得體": ("a", "", ""),
    "快要": ("r", "", ""),
    "情不自禁": ("a,v", "idiom", ""),
    "情有獨鍾": ("v", "idiom", ""),
    "明亮": ("a", "", ""),
    "明確": ("a,v", "", ""),
    "最差": ("a", "", ""),
    "無私": ("a", "", ""),
    "登入": ("n,v", "", ""),
    "直擊": ("n,v", "", ""),
    "相安無事": ("a,v", "idiom", ""),
    "簡陋": ("a", "", ""),
    "絕情": ("a", "", ""),
    "緣分": ("n", "", ""),
    "耐心": ("a,n", "", ""),
    "舒緩": ("a,v", "", ""),
    "衝破": ("v", "", ""),
    "鈍": ("a", "", ""),
    "錯失": ("n,v", "", ""),
    "閒聊": ("n,v", "", ""),
    "隱形": ("a,v", "", ""),
    "離場": ("n,v", "", ""),
    "首次": ("a,r", "", ""),
    "得心應手": ("a", "idiom", ""),
    "日新月異": ("a,v", "idiom", ""),
    "世界銀行": ("n", "", ""),
    "學術研究": ("n", "", ""),
    "艱苦奮鬥": ("n,v", "idiom", ""),
    "水土保持": ("n", "", ""),
    "發揚光大": ("v", "idiom", ""),
    "膠原蛋白": ("n", "", ""),
    "公投": ("n,v", "", ""),
    "天涯海角": ("n", "idiom", ""),
    "期末考試": ("n", "", ""),
    "籠統": ("a", "", ""),
    "威懾": ("n,v", "", ""),
    "忘記密碼": ("n,v", "", ""),
    "慈善事業": ("n", "", ""),
    "措手不及": ("a,v", "idiom", ""),
    "民主黨派": ("n", "", ""),
    "古典音樂": ("n", "", ""),
    "哈根達斯": ("n", "", ""),
    "耳目一新": ("a", "idiom", ""),
    "西伯利亞": ("n", "", ""),
    "百科全書": ("n", "", ""),
    "不動聲色": ("a", "idiom", ""),
    "格魯吉亞": ("n", "", ""),
    "妥善處理": ("v", "", ""),
    "從此以後": ("r", "", ""),
    "社會事業": ("n", "", ""),
    "罕": ("a", "", ""),
    "保護環境": ("n,v", "", ""),
    "紅人": ("n", "", ""),
    "分拆": ("n,v", "", ""),
    "一應俱全": ("a", "idiom", ""),
    "財政預算": ("n", "", ""),
    "視頻會議": ("n", "", ""),
    "送貨上門": ("n,v", "", ""),
    "刑事責任": ("n", "", ""),
    "有心人": ("n", "", ""),
    "錯綜複雜": ("a", "idiom", ""),
    "風花雪月": ("n", "idiom", ""),
    "塵埃落定": ("v", "idiom", ""),
    "優惠價": ("n", "", ""),
    "弄虛作假": ("v", "idiom", ""),
    "瘦小": ("a", "", ""),
    "軍委": ("n", "", ""),
    "俗人": ("n", "", ""),
    "遊刃有餘": ("a", "idiom", ""),
    "高分辨率": ("a,n", "", ""),
    "全力支持": ("n,v", "", ""),
    "馬爾代夫": ("n", "", ""),
    "切實可行": ("a", "idiom", ""),
    "市場準入": ("n", "", ""),
    "事半功倍": ("a,v", "idiom", ""),
    "人民警察": ("n", "", ""),
    "國際關係": ("n", "", ""),
    "近在咫尺": ("a", "idiom", ""),
    "夜深人靜": ("a,n", "idiom", ""),
    "放療": ("n,v", "", ""),
    "二流": ("a,n", "", ""),
    "市場機制": ("n", "", ""),
    "撲面而來": ("v", "idiom", ""),
    "至愛": ("a,n", "", ""),
    "軟件企業": ("n", "", ""),
    "傷痕累累": ("a", "idiom", ""),
    "化學成分": ("n", "", ""),
    "錦上添花": ("v", "idiom", ""),
    "匯市": ("n", "", ""),
    "心滿意足": ("a", "idiom", ""),
    "青黴素": ("n", "", ""),
    "世界大戰": ("n", "", ""),
    "墊底": ("n,v", "", ""),
    "特例": ("n", "", ""),
    "統一戰線": ("n", "", ""),
    "網絡管理": ("n", "", ""),
    "函授": ("n,v", "", ""),
    "生活態度": ("n", "", ""),
    "基本建設": ("n", "", ""),
    "社會秩序": ("n", "", ""),
    "阿拉斯加": ("n", "", ""),
    "噩耗": ("n", "", ""),
    "推拿": ("n,v", "", ""),
    "喜人": ("a", "", ""),
    "生產方式": ("n", "", ""),
    "避險": ("n,v", "", ""),
    "長期投資": ("n", "", ""),
    "密不可分": ("a", "idiom", ""),
    "網誌": ("n", "", ""),
    "航天飛機": ("n", "", ""),
    "億萬富翁": ("n", "", ""),
    "水運": ("n", "", ""),
    "年邁": ("a", "", ""),
    "組織領導": ("n,v", "", ""),
    "總工程師": ("n", "", ""),
    "面目全非": ("a", "idiom", ""),
    "保加利亞": ("n", "", ""),
    "撕心裂肺": ("a", "idiom", ""),
    "緊鑼密鼓": ("a,r", "idiom", ""),
    "勢在必行": ("a", "idiom", ""),
    "娛樂節目": ("n", "", ""),
    "民調": ("n", "", ""),
    "絕對優勢": ("n", "", ""),
    "絡繹不絕": ("a,v", "idiom", ""),
    "網絡應用": ("n", "", ""),
    "斯里蘭卡": ("n", "", ""),
    "公共關係": ("n", "", ""),
    "前提條件": ("n", "", ""),
    "薄弱環節": ("n", "", ""),
    "不過如此": ("a,r", "", ""),
    "如願以償": ("v", "idiom", ""),
    "行政區劃": ("n", "", ""),
    "天馬行空": ("a", "idiom", ""),
    "煙消雲散": ("v", "idiom", ""),
    "塞爾維亞": ("n", "", ""),
    "更新換代": ("n,v", "", ""),
    "小道消息": ("n", "", ""),
    "響應時間": ("n", "", ""),
    "平緩": ("a", "", ""),
    "敬業精神": ("n", "", ""),
    "物理學家": ("n", "", ""),
    "穿越時空": ("n,v", "", ""),
    "橫空出世": ("v", "idiom", ""),
    "意味深長": ("a", "idiom", ""),
    "意猶未盡": ("a", "idiom", ""),
    "大張旗鼓": ("a,r", "idiom", ""),
    "承租": ("v", "", ""),
    "延後": ("n,v", "", ""),
    "悄無聲息": ("a,r", "idiom", ""),
    "電子信箱": ("n", "", ""),
    "參差不齊": ("a", "idiom", ""),
    "增肥": ("v", "", ""),
    "大江南北": ("n,r", "", ""),
    "法律效力": ("n", "", ""),
    "一絲不苟": ("a", "idiom", ""),
    "公共設施": ("n", "", ""),
    "更衣": ("v", "", ""),
    "空戰": ("n", "", ""),
    "廠家直銷": ("n,v", "", ""),
    "鄙夷": ("n,v", "", ""),
    "忍者神龜": ("n", "", ""),
    "無濟於事": ("a,v", "idiom", ""),
    "絞盡腦汁": ("v", "idiom", ""),
    "毋庸置疑": ("a,r", "idiom", ""),
    "獨樹一幟": ("a,v", "idiom", ""),
    "視頻聊天": ("n,v", "", ""),
    "預習": ("n,v", "", ""),
    "鮮有": ("a,r", "", ""),
    "大出血": ("n,v", "", ""),
    "大勢所趨": ("n", "idiom", ""),
    "大可不必": ("a,r", "", ""),
    "按部就班": ("a,v", "idiom", ""),
    "無私奉獻": ("n,v", "", ""),
    "結業": ("n,v", "", ""),
    "一言不發": ("v", "idiom", ""),
    "學位論文": ("n", "", ""),
    "對衝基金": ("n", "", ""),
    "補足": ("v", "", ""),
    "古今中外": ("n,r", "", ""),
    "坦蕩": ("a", "", ""),
    "漫無目的": ("a", "", ""),
    "刑事拘留": ("n,v", "", ""),
    "毛細血管": ("n", "", ""),
    "晶瑩剔透": ("a", "idiom", ""),
    "物質生活": ("n", "", ""),
    "睡懶覺": ("v", "", ""),
    "吵吵": ("a,v", "", ""),
    "執行董事": ("n", "", ""),
    "技術指導": ("n,v", "", ""),
    "後期製作": ("n", "", ""),
    "癟": ("a", "", ""),
    "社會工作": ("n", "", ""),
    "開拓創新": ("n,v", "", ""),
    "不堪一擊": ("a", "idiom", ""),
    "居住環境": ("n", "", ""),
    "曇花一現": ("a,v", "idiom", ""),
    "炙手可熱": ("a", "idiom", ""),
    "五星紅旗": ("n", "", ""),
    "消腫": ("n,v", "", ""),
    "社區建設": ("n", "", ""),
    "耶路撒冷": ("n", "", ""),
    "金屬材料": ("n", "", ""),
    "助學貸款": ("n", "", ""),
    "不能自拔": ("a,v", "", ""),
    "勞斯萊斯": ("n", "", ""),
    "如何是好": ("x", "", "套語／嘆問"),
    "酸楚": ("a,n", "", ""),
    "高層建築": ("n", "", ""),
    "一家大細": ("n", "", "粵：全家大小"),
    "一聲令下": ("n,r", "", ""),
    "不妥": ("a", "", ""),
    "人仔細細": ("a,r", "", "粵：仔細"),
    "傻女": ("n", "", ""),
    "內戰": ("n", "", ""),
    "出謀劃策": ("v", "idiom", ""),
    "出雙入對": ("a,v", "idiom", ""),
    "半夜三更": ("n,r", "idiom", ""),
    "哀": ("a,n,v", "", ""),
    "坦率": ("a", "", ""),
    "大粒": ("a,n", "", "粵亦可指大人物"),
    "常常": ("r", "", ""),
    "強求": ("v", "", ""),
    "性交": ("n,v", "", ""),
    "拒": ("v", "", ""),
    "放走": ("v", "", ""),
    "束手無策": ("a", "idiom", ""),
    "樂意": ("a,v", "", ""),
    "無異": ("a", "", ""),
    "無緣": ("a,v", "", ""),
    "獨一無二": ("a", "idiom", ""),
    "當真": ("r,v", "", ""),
    "瘦削": ("a", "", ""),
    "相聚": ("n,v", "", ""),
    "眼仔碌碌": ("a", "", "粵：目光溜轉"),
    "福音": ("n", "", ""),
    "稍微": ("r", "", ""),
    "端正": ("a,v", "", ""),
    "簡潔": ("a", "", ""),
    "糟糕": ("a", "", ""),
    "自作多情": ("a,v", "idiom", ""),
    "舊日": ("n", "", ""),
    "見怪不怪": ("a,v", "idiom", ""),
    "謙虛": ("a", "", ""),
    "過分": ("a,r", "", ""),
    "過於": ("r", "", ""),
    "陸續": ("r", "", ""),
    "零星": ("a", "", ""),
    "靜默": ("a,n,v", "", ""),
    "首要": ("a", "", ""),
    "高聲": ("a,r", "", ""),
    "高調": ("a,n", "", ""),
    "不一會": ("r", "", ""),
    "偏頗": ("a", "", ""),
    "大行其道": ("v", "idiom", ""),
    "獨立思考": ("n,v", "", ""),
    "連帶責任": ("n", "", ""),
    "功不可沒": ("a", "idiom", ""),
    "國際慣例": ("n", "", ""),
    "流行病學": ("n", "", ""),
    "百事可樂": ("n", "", ""),
    "風情萬種": ("a", "idiom", ""),
    "人格魅力": ("n", "", ""),
    "屢見不鮮": ("a", "idiom", ""),
    "歸根結底": ("r", "idiom", ""),
    "目標管理": ("n", "", ""),
    "反派": ("n", "", ""),
    "大相徑庭": ("a", "idiom", ""),
    "冠冕堂皇": ("a", "idiom", ""),
    "謙遜": ("a", "", ""),
    "勞保": ("n", "", ""),
    "屈指可數": ("a", "idiom", ""),
    "欲哭無淚": ("a", "idiom", ""),
    "藍天白雲": ("n", "", ""),
    "不一會兒": ("r", "", ""),
    "匪徒": ("n", "", ""),
    "南斯拉夫": ("n", "", ""),
    "嚴酷": ("a", "", ""),
    "雨後春筍": ("n,v", "idiom", ""),
    "散漫": ("a", "", ""),
    "水到渠成": ("a,v", "idiom", ""),
    "特立獨行": ("a", "idiom", ""),
    "經濟特區": ("n", "", ""),
    "人工流產": ("n,v", "", ""),
    "卸任": ("v", "", ""),
    "若有所思": ("a", "idiom", ""),
    "房產中介": ("n", "", ""),
    "手足無措": ("a", "idiom", ""),
    "天人合一": ("n", "idiom", ""),
    "生物鐘": ("n", "", ""),
    "雞皮疙瘩": ("n", "", ""),
    "肅穆": ("a", "", ""),
    "五角大樓": ("n", "", ""),
    "小寫": ("n,v", "", ""),
    "生物化學": ("n", "", ""),
    "相對而言": ("r", "", ""),
    "老練": ("a", "", ""),
    "中國文學": ("n", "", ""),
    "問心無愧": ("a", "idiom", ""),
    "杜撰": ("v", "", ""),
    "管理功能": ("n", "", ""),
    "蕩然無存": ("a,v", "idiom", ""),
    "電磁輻射": ("n", "", ""),
    "合規": ("a,n", "", ""),
    "小民": ("n", "", ""),
    "心有靈犀": ("a,n", "idiom", ""),
    "稽核": ("n,v", "", ""),
    "主題公園": ("n", "", ""),
    "不同尋常": ("a", "", ""),
    "僅此而已": ("r", "", ""),
    "大專院校": ("n", "", ""),
    "文藝演出": ("n", "", ""),
    "欲罷不能": ("a,v", "", ""),
    "發生關係": ("v", "", ""),
    "社會活動": ("n", "", ""),
    "拒收": ("v", "", ""),
    "瞭如指掌": ("a,v", "idiom", ""),
    "刑事訴訟": ("n", "", ""),
    "女主人公": ("n", "", ""),
    "開發環境": ("n", "", ""),
    "信心十足": ("a", "", ""),
    "大千世界": ("n", "", ""),
    "大汗淋漓": ("a", "idiom", ""),
    "攀爬": ("n,v", "", ""),
    "白俄羅斯": ("n", "", ""),
    "風平浪靜": ("a", "idiom", ""),
    "必然性": ("n", "", ""),
    "悲歡離合": ("n", "idiom", ""),
    "認識自己": ("v", "", ""),
    "貧寒": ("a", "", ""),
    "夢中情人": ("n", "", ""),
    "大打出手": ("v", "", ""),
    "大腸桿菌": ("n", "", ""),
    "五彩繽紛": ("a", "idiom", ""),
    "國際象棋": ("n", "", ""),
    "史前": ("a,n", "", ""),
    "民族英雄": ("n", "", ""),
    "生態農業": ("n", "", ""),
    "太平天國": ("n", "", ""),
    "無瑕": ("a", "", ""),
    "身臨其境": ("a,v", "idiom", ""),
    "安居樂業": ("v", "idiom", ""),
    "工作小組": ("n", "", ""),
    "煥然一新": ("a", "idiom", ""),
    "相濡以沫": ("v", "idiom", ""),
    "科學管理": ("n", "", ""),
    "缺位": ("n,v", "", ""),
    "茶餘飯後": ("n,r", "idiom", ""),
}


def _norm_pos(pos: str) -> str:
    if pos == "u":
        return "u"
    tags = sorted(set(t.strip() for t in pos.split(",") if t.strip()))
    order = {"a": 0, "n": 1, "r": 2, "v": 3, "x": 4}
    tags = sorted(tags, key=lambda t: order.get(t, 9))
    return ",".join(tags)


def main() -> None:
    rows_in = list(csv.DictReader(TSV.open(encoding="utf-8"), delimiter="\t"))
    assert len(rows_in) == 400, len(rows_in)
    missing = [r["literal"] for r in rows_in if r["literal"] not in L]
    extra = set(L) - {r["literal"] for r in rows_in}
    if missing or extra:
        raise SystemExit(f"missing={missing[:20]} extra={list(extra)[:20]}")

    out_rows = []
    for r in rows_in:
        pos, fam, note = L[r["literal"]]
        pos = _norm_pos(pos)
        if fam not in ("", "idiom"):
            raise SystemExit(f"bad family {r['literal']} {fam}")
        if pos == "u" and not note:
            raise SystemExit(f"u needs note: {r['literal']}")
        out_rows.append(
            {
                "literal": r["literal"],
                "freq": r["freq"],
                "pos": pos,
                "family": fam,
                "voice": "",
                "note": note if pos == "u" or note else "",
            }
        )

    # keep notes only for u (task: note typically u); strip non-u notes for clean TSV
    # but prior summaries keep borderline notes — keep notes as set for non-empty useful
    for row in out_rows:
        if row["pos"] != "u":
            # strip notes for formal to match prior clean TSV style (nf part3 mostly empty notes)
            row["note"] = ""

    with TSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["literal", "freq", "pos", "family", "voice", "note"],
            delimiter="\t",
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(out_rows)

    # counts
    formal = sum(1 for r in out_rows if r["pos"] != "u")
    u_n = sum(1 for r in out_rows if r["pos"] == "u")
    pos_c = Counter(r["pos"] for r in out_rows)
    single = {"n": 0, "v": 0, "a": 0, "r": 0, "x": 0}
    multi = 0
    tag_inc = Counter()
    for r in out_rows:
        p = r["pos"]
        if p == "u":
            continue
        tags = p.split(",")
        for t in tags:
            tag_inc[t] += 1
        if len(tags) == 1 and p in single:
            single[p] += 1
        elif len(tags) >= 2:
            multi += 1
    idiom_rows = [r for r in out_rows if r["family"] == "idiom"]
    voice_ne = sum(1 for r in out_rows if r["voice"])

    def pct(n: int) -> str:
        return f"{100 * n / 400:.1f}%"

    lines = []
    lines.append("# u_inlex_top2000_nf2 manual POS — part3")
    lines.append("")
    lines.append("**File:** `data/pos/audit/u_inlex_top2000_nf2/label_part3.tsv`")
    lines.append("**Universe:** in-lexicon still-`u` · essay top2000 non-fragment · part3 · **400** rows")
    lines.append("**Date:** 2026-07-19")
    lines.append("")
    lines.append(
        "**Rules:** `n/v/a/r/x` multi-ok（逗號、字母序 `a,n,r,v,x`）；`u` 僅真正截斷／殘片；"
        "`family=idiom` 只標清晰熟語；`voice` 全空；`note` 只標 `u` 理由。"
    )
    lines.append("")
    lines.append("## Counts formal vs u")
    lines.append("")
    lines.append("| bucket | n | % |")
    lines.append("|--------|--:|---:|")
    lines.append(f"| formal（非 u） | {formal} | {pct(formal)} |")
    lines.append(f"| `u` fragment/opaque | {u_n} | {pct(u_n)} |")
    lines.append(f"| **total** | **400** | 100% |")
    lines.append("")
    lines.append("### Single-tag vs multi")
    lines.append("")
    lines.append("| pos 模式 | n |")
    lines.append("|----------|--:|")
    for k in ("n", "v", "a", "r", "x"):
        lines.append(f"| `{k}` only | {single[k]} |")
    lines.append(f"| multi（≥2 tags） | {multi} |")
    lines.append(f"| `u` | {u_n} |")
    lines.append(f"| `family=idiom` | {len(idiom_rows)} |")
    lines.append(f"| voice non-empty | {voice_ne} |")
    lines.append("| **total** | **400** |")
    lines.append("")
    lines.append("### Tag incidence（row 含該 tag；multi 可重疊）")
    lines.append("")
    lines.append("| tag | rows |")
    lines.append("|-----|-----:|")
    for t in ("n", "v", "a", "r", "x", "u"):
        if t == "u":
            lines.append(f"| u | {u_n} |")
        else:
            lines.append(f"| {t} | {tag_inc[t]} |")
    lines.append(f"| multi rows | {multi} |")
    lines.append("")
    lines.append("### `family=idiom`")
    lines.append("")
    lines.append("| literal | pos |")
    lines.append("|---------|-----|")
    for r in idiom_rows:
        lines.append(f"| {r['literal']} | {r['pos']} |")
    lines.append("")
    if u_n:
        lines.append("### `u` keep")
        lines.append("")
        lines.append("| literal | note |")
        lines.append("|---------|------|")
        for r in out_rows:
            if r["pos"] == "u":
                lines.append(f"| {r['literal']} | {r['note']} |")
        lines.append("")
    else:
        lines.append("### `u` keep")
        lines.append("")
        lines.append("（無：本批 400 皆可標 formal）")
        lines.append("")

    lines.append("## Formal patterns")
    lines.append("")
    lines.append("1. **專名／品牌／地名／機構 → `n`**：莎士比亞、哈根達斯、勞斯萊斯、百事可樂、忍者神龜；西伯利亞、格魯吉亞、馬爾代夫、阿拉斯加、保加利亞、斯里蘭卡、塞爾維亞、耶路撒冷、白俄羅斯、南斯拉夫；世界銀行、國際足聯、五角大樓、太平天國")
    lines.append("2. **政經／科技／社會名物 → `n`**：中央銀行、核心價值、財政預算、市場準入、對衝基金、膠原蛋白、青黴素、大腸桿菌、開發環境、經濟特區")
    lines.append("3. **名動 dual → `n,v`**：激化、現場直播、公關、登入、直擊、分拆、放療、墊底、避險、更新換代、廠家直銷、預習、大出血、消腫、人工流產、小寫、稽核、攀爬、缺位")
    lines.append("4. **形／副／虛**：憨厚、嬌小、得體、簡陋、籠統、坦蕩、嚴酷、謙遜；自古以來、快要、從此以後、稍微、過於、陸續、不一會(兒)、相對而言、僅此而已；何時`r,x`；大吉利是／如何是好`x`")
    lines.append("5. **粵語常用**：大吉利是、一家大細、人仔細細、眼仔碌碌、大粒、傻女")
    lines.append(f"6. **熟語 family=idiom**：{len(idiom_rows)} 條清晰四字／固定熟語（見上表）")
    lines.append("")
    lines.append("## Policy notes")
    lines.append("")
    lines.append("1. **唔造 POS：** 本批無真截斷／殘片；`u`=0。")
    lines.append("2. **multi 從嚴：** 只標兩棲皆常見；主標不清先單標。")
    lines.append("3. **family：** 清晰固定熟語標 `idiom`；現代複合／自由短語不標；voice 全空。")
    lines.append("4. **下一步：** 與 part1–2／4–5 合併後可 `_apply.py` upsert（note 帶 `u-inlex-nf2b`）再抽 gate sample。")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("| path | role |")
    lines.append("|------|------|")
    lines.append("| `data/pos/audit/u_inlex_top2000_nf2/label_part3.tsv` | 400 列已填 pos（overwrite） |")
    lines.append("| `data/pos/audit/u_inlex_top2000_nf2/label_part3_summary.md` | 本摘要 |")
    lines.append("")

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"formal={formal} u={u_n} idiom={len(idiom_rows)}")
    print(f"pos modes: {pos_c.most_common(15)}")


if __name__ == "__main__":
    main()
