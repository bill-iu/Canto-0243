# one-shot fill for label_part2.tsv — not part of runtime pipeline
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

DIR = Path(__file__).resolve().parent
TSV = DIR / "label_part2.tsv"
SUMMARY = DIR / "label_part2_summary.md"

# literal -> (pos, family, note); multi tags alpha-sorted a,n,r,v,x
# family '' | 'idiom'; note only for u / rare borderline
L: dict[str, tuple[str, str, str]] = {
    "剖腹自殺": ("v", "", ""),
    "品格高尚": ("a", "", ""),
    "多重選擇": ("n", "", ""),
    "大氣壓強": ("n", "", ""),
    "嫁狗隨狗": ("v,x", "idiom", ""),
    "微細加工": ("n", "", ""),
    "洗手不幹": ("v", "idiom", ""),
    "獨裁政權": ("n", "", ""),
    "琴瑟和鳴": ("a,v", "idiom", ""),
    "絕食抗議": ("n,v", "", ""),
    "經院哲學": ("n", "", ""),
    "蠶食鯨吞": ("v", "idiom", ""),
    "辯證邏輯": ("n", "", ""),
    "鏡像站點": ("n", "", ""),
    "黃花梨木": ("n", "", ""),
    "伽瑪射線": ("n", "", ""),
    "克己復禮": ("v", "idiom", ""),
    "升斗小民": ("n", "idiom", ""),
    "將門虎子": ("n", "idiom", ""),
    "成年累月": ("r", "idiom", ""),
    "拖延戰術": ("n", "", ""),
    "敵我矛盾": ("n", "", ""),
    "文人相輕": ("a,v", "idiom", ""),
    "春秋繁露": ("n", "", ""),
    "用兵如神": ("a,v", "idiom", ""),
    "略見一斑": ("v", "idiom", ""),
    "簡單勞動": ("n", "", ""),
    "紫外線光": ("n", "", ""),
    "羥基丁酸": ("n", "", ""),
    "羥自由基": ("n", "", ""),
    "膽識過人": ("a", "", ""),
    "舐犢情深": ("a", "idiom", ""),
    "虎皮鸚鵡": ("n", "", ""),
    "起重葫蘆": ("n", "", ""),
    "身歷其境": ("a,v", "idiom", ""),
    "首尾相接": ("a,v", "", ""),
    "一般情形": ("n", "", ""),
    "三跪九叩": ("n,v", "", ""),
    "久病成醫": ("a,x", "idiom", ""),
    "克己奉公": ("v", "idiom", ""),
    "全能運動": ("n", "", ""),
    "加足馬力": ("v", "", ""),
    "包打天下": ("v", "", ""),
    "另眼相待": ("v", "", ""),
    "同工不同酬": ("n", "", ""),
    "夫妻反目": ("a,v", "", ""),
    "官樣文章": ("n", "idiom", ""),
    "彈撥樂器": ("n", "", ""),
    "心存不滿": ("a,v", "", ""),
    "排列次序": ("n", "", ""),
    "擁兵自重": ("v", "idiom", ""),
    "流水不腐": ("a,x", "idiom", ""),
    "白日見鬼": ("v,x", "idiom", ""),
    "碩大無朋": ("a", "idiom", ""),
    "統一資源": ("n", "", ""),
    "貴族身份": ("n", "", ""),
    "費利克斯": ("n", "", ""),
    "隱形飛機": ("n", "", ""),
    "麥芽糖醇": ("n", "", ""),
    "一脈相傳": ("a,v", "idiom", ""),
    "丟盔卸甲": ("v", "idiom", ""),
    "保持原貌": ("v", "", ""),
    "公共假期": ("n", "", ""),
    "口頭文學": ("n", "", ""),
    "寡廉鮮恥": ("a", "idiom", ""),
    "形勢逼人": ("a", "", ""),
    "忠君愛國": ("a,v", "", ""),
    "慎重其事": ("a,v", "", ""),
    "撒馬爾罕": ("n", "", ""),
    "濫伐林木": ("v", "", ""),
    "究其根源": ("v", "", ""),
    "精子密度": ("n", "", ""),
    "肝膽俱裂": ("a,v", "idiom", ""),
    "舊約全書": ("n", "", ""),
    "過境簽證": ("n", "", ""),
    "違禁藥品": ("n", "", ""),
    "項上人頭": ("n", "idiom", ""),
    "餓虎撲食": ("v", "idiom", ""),
    "高麗王朝": ("n", "", ""),
    "一般狀況": ("n", "", ""),
    "人道精神": ("n", "", ""),
    "偷食禁果": ("v", "", ""),
    "勻速運動": ("n", "", ""),
    "地靈人傑": ("a,x", "idiom", ""),
    "工科學生": ("n", "", ""),
    "後進先出": ("n", "", ""),
    "有損壓縮": ("n", "", ""),
    "木管樂器": ("n", "", ""),
    "橫幅標語": ("n", "", ""),
    "浩氣長存": ("a,v", "", ""),
    "消費基金": ("n", "", ""),
    "疑問代詞": ("n", "", ""),
    "疲勞轟炸": ("n,v", "", ""),
    "瞎子摸象": ("n,v", "idiom", ""),
    "細微末節": ("n", "idiom", ""),
    "絕對地址": ("n", "", ""),
    "總務主任": ("n", "", ""),
    "缺心眼兒": ("a,n", "", ""),
    "罪不可赦": ("a", "", ""),
    "良家女子": ("n", "", ""),
    "開會時間": ("n", "", ""),
    "魂飛天外": ("a,v", "", ""),
    "魚肉百姓": ("v", "idiom", ""),
    "一觸即潰": ("a,v", "idiom", ""),
    "上陣殺敵": ("v", "", ""),
    "互有勝負": ("a,v", "", ""),
    "互致問候": ("v", "", ""),
    "代罪羔羊": ("n", "idiom", ""),
    "傳真發送": ("n,v", "", ""),
    "冰上運動": ("n", "", ""),
    "勇冠三軍": ("a", "idiom", ""),
    "半機械化": ("a,n", "", ""),
    "同盟條約": ("n", "", ""),
    "地主家庭": ("n", "", ""),
    "失信於人": ("a,v", "", ""),
    "奇文共賞": ("v,x", "idiom", ""),
    "孰能無過": ("x", "idiom", ""),
    "少管閒事": ("v", "", ""),
    "愧不敢當": ("a,x", "", ""),
    "教導有方": ("a", "", ""),
    "日光浴室": ("n", "", ""),
    "有失身份": ("a,v", "", ""),
    "樹上開花": ("n,v", "", ""),
    "清水衙門": ("n", "idiom", ""),
    "無則加勉": ("v", "idiom", "成語截；有則改之無則加勉"),
    "眉目清秀": ("a", "", ""),
    "知情不報": ("v", "", ""),
    "空氣取樣": ("n,v", "", ""),
    "缺衣少食": ("a", "", ""),
    "股票代號": ("n", "", ""),
    "誤上賊船": ("v", "idiom", ""),
    "開門揖盜": ("v", "idiom", ""),
    "驕兵必敗": ("a,x", "idiom", ""),
    "黑白不分": ("a,v", "", ""),
    "不加選擇": ("a,r", "", ""),
    "事務律師": ("n", "", ""),
    "便宜行事": ("v", "", ""),
    "公民義務": ("n", "", ""),
    "出入平安": ("x", "", ""),
    "失道寡助": ("a,x", "idiom", ""),
    "女繼承人": ("n", "", ""),
    "婚喪喜慶": ("n", "", ""),
    "婚生子女": ("n", "", ""),
    "孝子賢孫": ("n", "", ""),
    "客觀真理": ("n", "", ""),
    "尋根問底": ("v", "", ""),
    "淺斟低唱": ("v", "", ""),
    "神智清醒": ("a", "", ""),
    "結社自由": ("n", "", ""),
    "聖母教堂": ("n", "", ""),
    "胸腺嘧啶": ("n", "", ""),
    "虧本出售": ("v", "", ""),
    "逗人喜愛": ("a", "", ""),
    "遠隔重洋": ("a,v", "", ""),
    "七零八碎": ("a,n", "", ""),
    "傀儡政權": ("n", "", ""),
    "大專學生": ("n", "", ""),
    "導彈潛艇": ("n", "", ""),
    "愛人如己": ("v", "idiom", ""),
    "慷慨就義": ("v", "", ""),
    "懸樑刺股": ("n,v", "idiom", ""),
    "海關官員": ("n", "", ""),
    "漢坦病毒": ("n", "", ""),
    "無遠弗屆": ("a,v", "idiom", ""),
    "皇天后土": ("n,x", "idiom", ""),
    "眼梢": ("n", "", ""),
    "老於世故": ("a", "", ""),
    "萬頃碧波": ("n", "", ""),
    "過時不候": ("v,x", "", ""),
    "邪不勝正": ("a,x", "idiom", ""),
    "鋤強扶弱": ("v", "", ""),
    "陸海空軍": ("n", "", ""),
    "離情別緒": ("n", "", ""),
    "鬧鈴時鐘": ("n", "", ""),
    "一無所長": ("a", "idiom", ""),
    "上中下游": ("n", "", ""),
    "了無新意": ("a", "", ""),
    "五卅運動": ("n", "", ""),
    "以儆效尤": ("v", "idiom", ""),
    "再造手術": ("n", "", ""),
    "同氣連枝": ("a,n", "idiom", ""),
    "大漢民族": ("n", "", ""),
    "孟加拉語": ("n", "", ""),
    "實不相瞞": ("r,x", "", ""),
    "實況錄音": ("n", "", ""),
    "寬宏大度": ("a", "", ""),
    "強迫觀念": ("n", "", ""),
    "支付得起": ("a,v", "", ""),
    "政治避難": ("n", "", ""),
    "機關刊物": ("n", "", ""),
    "殺富濟貧": ("v", "", ""),
    "消極性": ("n", "", ""),
    "深耕細作": ("v", "", ""),
    "滿口髒話": ("n,v", "", ""),
    "狼多肉少": ("a", "idiom", ""),
    "福壽雙全": ("a", "", ""),
    "苦難深重": ("a", "", ""),
    "西班牙港": ("n", "", ""),
    "革命意志": ("n", "", ""),
    "鬧着玩兒": ("v", "", ""),
    "一哄而起": ("v", "", ""),
    "一枕黃粱": ("n,v", "idiom", ""),
    "人民起義": ("n", "", ""),
    "位極人臣": ("a,v", "", ""),
    "典型調查": ("n", "", ""),
    "分形幾何": ("n", "", ""),
    "反射療法": ("n", "", ""),
    "各執己見": ("v", "", ""),
    "國外貿易": ("n", "", ""),
    "士農工商": ("n", "", ""),
    "專心一意": ("a,r", "", ""),
    "打落水狗": ("v", "idiom", ""),
    "找不自在": ("v", "", ""),
    "掐頭去尾": ("v", "", ""),
    "時有所聞": ("a,v", "", ""),
    "楚漢戰爭": ("n", "", ""),
    "狀態參數": ("n", "", ""),
    "禁止停車": ("v,x", "", ""),
    "窮於應付": ("a,v", "", ""),
    "見馬克思": ("v", "", ""),
    "警民衝突": ("n", "", ""),
    "踏青賞花": ("v", "", ""),
    "身心交瘁": ("a", "", ""),
    "道德認識": ("n", "", ""),
    "金融風波": ("n", "", ""),
    "釣魚執法": ("n,v", "", ""),
    "陽關大道": ("n", "idiom", ""),
    "隨風倒": ("a,v", "", ""),
    "集腋成裘": ("v", "idiom", ""),
    "電磁理論": ("n", "", ""),
    "高風險區": ("n", "", ""),
    "魯莽行事": ("v", "", ""),
    "加油添醋": ("v", "idiom", ""),
    "參差錯落": ("a", "", ""),
    "唱空城計": ("v", "", ""),
    "奏鳴曲式": ("n", "", ""),
    "山高水遠": ("a", "", ""),
    "後西遊記": ("n", "", ""),
    "從有到無": ("r", "", ""),
    "未能免俗": ("a,v", "", ""),
    "東坡肘子": ("n", "", ""),
    "歸根究底": ("r", "", ""),
    "獨身生活": ("n", "", ""),
    "生物測定": ("n", "", ""),
    "留話": ("v", "", ""),
    "腔腸動物": ("n", "", ""),
    "自有公論": ("v,x", "", ""),
    "行蹤不明": ("a", "", ""),
    "觀察入微": ("a,v", "", ""),
    "連中三元": ("v", "", ""),
    "駐顏有術": ("a,v", "", ""),
    "驚喜交集": ("a", "", ""),
    "不戰而退": ("v", "", ""),
    "分權制衡": ("n,v", "", ""),
    "另有企圖": ("a,v", "", ""),
    "名聲遠播": ("a,v", "", ""),
    "妙語如珠": ("a", "", ""),
    "悔恨交加": ("a", "", ""),
    "戊戌政變": ("n", "", ""),
    "永浴愛河": ("v", "", ""),
    "沼澤地帶": ("n", "", ""),
    "煎炸食品": ("n", "", ""),
    "理化因素": ("n", "", ""),
    "西薩摩亞": ("n", "", ""),
    "輕巧方便": ("a", "", ""),
    "辭不達意": ("a,v", "idiom", ""),
    "骨肉相殘": ("v", "", ""),
    "出將入相": ("n,v", "idiom", ""),
    "填海造地": ("n,v", "", ""),
    "威震八方": ("a,v", "", ""),
    "後人乘涼": ("v", "", "成語截；前人栽樹後人乘涼"),
    "核工業部": ("n", "", ""),
    "棉紡織業": ("n", "", ""),
    "橡皮圖章": ("n", "idiom", ""),
    "求才若渴": ("a,v", "idiom", ""),
    "無機可乘": ("a", "idiom", ""),
    "珠胎暗結": ("v", "idiom", ""),
    "瓜田李下": ("n", "idiom", ""),
    "磨拳擦掌": ("v", "idiom", ""),
    "社會平等": ("n", "", ""),
    "細菌武器": ("n", "", ""),
    "縱情聲色": ("v", "", ""),
    "臨界壓力": ("n", "", ""),
    "萬世師表": ("n", "idiom", ""),
    "連名帶姓": ("r,v", "", ""),
    "達魯花赤": ("n", "", ""),
    "靈犀相通": ("a,v", "", ""),
    "不得其法": ("a,v", "", ""),
    "不支倒地": ("v", "", ""),
    "人財兩失": ("a,v", "", ""),
    "動眼神經": ("n", "", ""),
    "印地安納": ("n", "", ""),
    "另請高明": ("v,x", "", ""),
    "四大石窟": ("n", "", ""),
    "夾起尾巴": ("v", "", ""),
    "守土有責": ("a,x", "", ""),
    "廣告條幅": ("n", "", ""),
    "性慾高潮": ("n", "", ""),
    "愛答不理": ("a,v", "", ""),
    "承先啓後": ("v", "idiom", ""),
    "施洗約翰": ("n", "", ""),
    "明升暗降": ("n,v", "", ""),
    "明槍易躲": ("a,x", "idiom", "成語截；明槍易躲暗箭難防"),
    "案頭工作": ("n", "", ""),
    "歷久彌堅": ("a", "", ""),
    "焚琴煮鶴": ("v", "idiom", ""),
    "用盡心機": ("v", "", ""),
    "疾風勁草": ("n,x", "idiom", ""),
    "真名實姓": ("n", "", ""),
    "移山填海": ("v", "", ""),
    "綱舉目張": ("v", "idiom", ""),
    "訪貧問苦": ("v", "", ""),
    "賣官鬻爵": ("v", "idiom", ""),
    "重力異常": ("n", "", ""),
    "飲彈自盡": ("v", "", ""),
    "七十二行": ("n", "", ""),
    "七孔流血": ("a,v", "", ""),
    "博學多聞": ("a", "", ""),
    "品質管制": ("n", "", ""),
    "因紐特人": ("n", "", ""),
    "地覆天翻": ("a,v", "idiom", ""),
    "大塊朵頤": ("v", "idiom", ""),
    "封頂儀式": ("n", "", ""),
    "年深日久": ("a,r", "", ""),
    "心膽俱裂": ("a,v", "", ""),
    "恍然醒悟": ("v", "", ""),
    "懷柔政策": ("n", "", ""),
    "拜科努爾": ("n", "", ""),
    "旅行裝備": ("n", "", ""),
    "有何指教": ("x", "", ""),
    "棋逢敵手": ("a,v", "idiom", ""),
    "死而不僵": ("a,v", "", "成語截；百足之蟲死而不僵"),
    "氣象報告": ("n", "", ""),
    "永誌不忘": ("v", "", ""),
    "空中格鬥": ("n", "", ""),
    "自有主張": ("a,v", "", ""),
    "良禽擇木": ("v", "idiom", "成語截；良禽擇木而棲"),
    "資料傳輸": ("n", "", ""),
    "邊防警察": ("n", "", ""),
    "鐵板牛肉": ("n", "", ""),
    "鑿壁偷光": ("n,v", "idiom", ""),
    "魔術方塊": ("n", "", ""),
    "鴉片貿易": ("n", "", ""),
}


def main() -> None:
    rows_in: list[dict[str, str]] = []
    with TSV.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            rows_in.append(dict(r))

    missing = [r["literal"] for r in rows_in if r["literal"] not in L]
    extra = sorted(set(L) - {r["literal"] for r in rows_in})
    if missing or extra:
        raise SystemExit(f"label map mismatch missing={missing[:20]} extra={extra[:20]}")

    out_rows: list[dict[str, str]] = []
    pos_c: Counter[str] = Counter()
    fam_c: Counter[str] = Counter()
    tag_hits: Counter[str] = Counter()
    multi = 0
    u_rows: list[tuple[str, str]] = []
    idiom_rows: list[tuple[str, str]] = []

    for r in rows_in:
        lit = r["literal"]
        pos, fam, note = L[lit]
        tags = [t.strip() for t in pos.split(",") if t.strip()]
        if pos != "u":
            tags = sorted(set(tags))
            pos = ",".join(tags)
        r["pos"] = pos
        r["family"] = fam
        r["voice"] = ""
        r["note"] = note
        out_rows.append(r)
        pos_c[pos] += 1
        fam_c[fam or "empty"] += 1
        if pos == "u":
            u_rows.append((lit, note))
        else:
            for t in tags:
                tag_hits[t] += 1
            if len(tags) > 1:
                multi += 1
        if fam == "idiom":
            idiom_rows.append((lit, pos))

    fieldnames = ["literal", "freq", "pos", "family", "voice", "note"]
    with TSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    n = len(out_rows)
    n_u = len(u_rows)
    n_formal = n - n_u
    n_idiom = len(idiom_rows)

    lines: list[str] = []
    lines.append("# u_inlex_top2000_nf5 manual POS label — part2")
    lines.append("")
    lines.append("**File:** `data/pos/audit/u_inlex_top2000_nf5/label_part2.tsv`")
    lines.append("**Universe slice:** in-lexicon still-`u` top2000_nf5 batch part2")
    lines.append(f"**n:** {n}")
    lines.append("**Date:** 2026-07-19")
    lines.append("")
    lines.append(
        "**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；"
        "`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由／成語截 borderline。"
    )
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append("| pos bucket | n | % |")
    lines.append("|------------|--:|---:|")
    lines.append(f"| formal（非 u） | {n_formal} | {100.0 * n_formal / n:.2f}% |")
    lines.append(f"| `u` fragment/unclear | {n_u} | {100.0 * n_u / n:.2f}% |")
    lines.append(f"| **total** | **{n}** | 100% |")
    lines.append("")
    lines.append("| family | n |")
    lines.append("|--------|--:|")
    lines.append(f"| empty | {fam_c.get('empty', 0)} |")
    lines.append(f"| `idiom` | {n_idiom} |")
    lines.append("| voice non-empty | 0 |")
    lines.append("")
    lines.append("### pos distribution（exact string）")
    lines.append("")
    lines.append("| pos | n |")
    lines.append("|-----|--:|")
    for pos, c in pos_c.most_common():
        lines.append(f"| {pos} | {c} |")
    lines.append("")
    lines.append("### Formal tag hits（multi 計入每個 tag；一列可多 hit）")
    lines.append("")
    lines.append("| tag | hits |")
    lines.append("|-----|-----:|")
    for t in ("n", "a", "r", "v", "x"):
        lines.append(f"| {t} | {tag_hits.get(t, 0)} |")
    lines.append(f"| multi rows | {multi} |")
    lines.append("")
    lines.append(f"## `u` patterns（{n_u}）")
    lines.append("")
    if n_u == 0:
        lines.append(
            "_None._ 本批 "
            f"{n} 列皆可標 formal（完整詞／固定短語／專名／科技 NP；無合成殘字或主謂截斷）。"
        )
        lines.append("")
        lines.append("**Full `u` list (0):** —")
    else:
        lines.append("| literal | note |")
        lines.append("|---------|------|")
        for lit, note in u_rows:
            lines.append(f"| {lit} | {note or '—'} |")
    lines.append("")
    lines.append(f"## `family=idiom`（{n_idiom}）")
    lines.append("")
    lines.append("| literal | pos |")
    lines.append("|---------|-----|")
    for lit, pos in idiom_rows:
        lines.append(f"| {lit} | {pos} |")
    lines.append("")
    lines.append(
        "未標 idiom（固定但非成語桶）：出入平安`x`（賀語）、有何指教`x`（客套）、"
        "禁止停車`v,x`（告示）、過時不候`v,x`（告示套語）、實不相瞞`r,x`（話語標記）、"
        "統一資源`n`（URI 術語根）、後進先出`n`（LIFO 術語）、有損壓縮`n`（lossy compression）、"
        "五卅運動／戊戌政變`n`（史專名）、樹上開花`n,v`（計謀名亦可作字面）。"
    )
    lines.append("")
    lines.append("## Formal patterns worth keeping")
    lines.append("")
    lines.append(
        "- **專名／地名／書名／品牌 → n**：春秋繁露、費利克斯、撒馬爾罕、舊約全書、高麗王朝、"
        "漢坦病毒、西班牙港、孟加拉語、楚漢戰爭、後西遊記、西薩摩亞、印地安納、施洗約翰、"
        "拜科努爾、達魯花赤、因紐特人、東坡肘子、魔術方塊"
    )
    lines.append(
        "- **科技／醫／政經 NP → n**：大氣壓強、微細加工、伽瑪射線、羥基丁酸、羥自由基、"
        "有損壓縮、絕對地址、胸腺嘧啶、分形幾何、反射療法、腔腸動物、臨界壓力、動眼神經、"
        "重力異常、資料傳輸、品質管制、麥芽糖醇、隱形飛機、導彈潛艇"
    )
    lines.append(
        "- **成語／熟語 → 多 a/v/r + family=idiom**：嫁狗隨狗、洗手不幹、琴瑟和鳴、克己復禮、"
        "升斗小民、將門虎子、成年累月、蠶食鯨吞、文人相輕、略見一斑、舐犢情深、擁兵自重、"
        "碩大無朋、丟盔卸甲、寡廉鮮恥、開門揖盜、集腋成裘、瓜田李下、焚琴煮鶴、鑿壁偷光…"
    )
    lines.append(
        "- **篇章／套語 → r,x／x**：出入平安、有何指教、實不相瞞、孰能無過、過時不候、禁止停車"
    )
    lines.append(
        "- **短詞 formal**：眼梢`n`、留話`v`、隨風倒`a,v`、消極性`n`"
    )
    lines.append("")
    lines.append("## Borderline（已標 formal；可再審）")
    lines.append("")
    lines.append("| literal | pos | note |")
    lines.append("|---------|-----|------|")
    lines.append("| 無則加勉 | v | 成語截「有則改之無則加勉」；family=idiom |")
    lines.append("| 後人乘涼 | v | 成語截「前人栽樹後人乘涼」；family 空 |")
    lines.append("| 明槍易躲 | a,x | 成語截「明槍易躲暗箭難防」；family=idiom |")
    lines.append("| 良禽擇木 | v | 成語截「良禽擇木而棲」；family=idiom |")
    lines.append("| 死而不僵 | a,v | 成語截「百足之蟲死而不僵」；family 空 |")
    lines.append("| 統一資源 | n | URI 術語根（統一資源定位符）；可再審 |")
    lines.append("| 出入平安 | x | 賀語；未標 idiom |")
    lines.append("| 有何指教 | x | 客套詢句；未標 idiom |")
    lines.append("| 禁止停車 | v,x | 告示／祈使 |")
    lines.append("| 樹上開花 | n,v | 三十六計名／字面動 |")
    lines.append("| 身歷其境 | a,v | 常作「身臨其境」異體；仍 formal idiom |")
    lines.append("| 磨拳擦掌 | v | 常作「摩拳擦掌」；仍 formal idiom |")
    lines.append("| 代罪羔羊 | n | 常作「替罪羔羊」；仍 formal idiom |")
    lines.append("| 見馬克思 | v | 死亡委婉語；可再審 x |")
    lines.append("")
    lines.append("## Policy notes")
    lines.append("")
    lines.append("1. **唔造 POS**：本批無合成殘字／主謂截斷 → `u`=0。")
    lines.append("2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。")
    lines.append(
        f"3. **family**：僅 {n_idiom} 條真成語／固定熟語標 `idiom`；能產短語、政經／科技 NP、"
        "賀語／告示套語 family 空。"
    )
    lines.append("4. **voice**：本批無語態對，全空。")
    lines.append(
        "5. **下一步**：與 part1／3–5 合併後可 `_apply.py` upsert（note 帶 `u-inlex-nf5`）再抽 gate sample。"
    )
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("| path | role |")
    lines.append("|------|------|")
    lines.append("| `data/pos/audit/u_inlex_top2000_nf5/label_part2.tsv` | "
                 f"{n} 列已填 pos |")
    lines.append("| `data/pos/audit/u_inlex_top2000_nf5/label_part2_summary.md` | 本摘要 |")
    lines.append("")

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {n} rows formal={n_formal} u={n_u} idiom={n_idiom}")
    print(f"pos_top={pos_c.most_common(12)}")
    print(f"tag_hits={dict(tag_hits)} multi={multi}")


if __name__ == "__main__":
    main()
