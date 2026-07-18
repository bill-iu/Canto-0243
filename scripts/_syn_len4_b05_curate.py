"""Curate syn_len4 batch-5 fixtures (ranks 2001–2500)."""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import normalize_literal  # noqa: E402
from ingest.project_antonyms import (  # noqa: E402
    DEFAULT_TSV as ANT_TSV,
    pair_undirected_key,
    parse_project_antonyms_tsv,
)
from ingest.project_synonyms import (  # noqa: E402
    DEFAULT_TSV,
    load_lexicon_literals,
    parse_project_synonyms_tsv,
)

FIXT = ROOT / "data" / "syn_ant" / "project" / "fixtures"
BATCH = "syn-len4-b05-20260718"

# head -> preferred near-synonym tail (must resolve into lexicon via pick_tail)
RAW: dict[str, str] = {
    "富可敵國": "腰纏萬貫",
    "殫精竭慮": "嘔心瀝血",
    "比較而言": "相對而言",
    "深有同感": "感同身受",
    "色情電影": "色情片",
    "豪情萬丈": "壯志凌雲",
    "走親訪友": "探親訪友",
    "一較高下": "一決高下",
    "不告而別": "不辭而別",
    "勝券在握": "穩操勝券",
    "勞動保險": "勞保",
    "抽絲剝繭": "條分縷析",
    "海外僑胞": "華僑",
    "錦繡前程": "大好前程",
    "伸張正義": "主持正義",
    "低頭不語": "默不作聲",
    "太陽電池": "太陽能電池",
    "心如刀絞": "心如刀割",
    "打小報告": "告密",
    "直角三角": "直角三角形",
    "神經過敏": "神經質",
    "通風報信": "通風報訊",
    "人壽保險": "壽險",
    "全盛時期": "全盛期",
    "八月十五": "中秋節",
    "唔使客氣": "別客氣",
    "大開眼界": "開眼界",
    "專有名詞": "專名",
    "平方英尺": "平方呎",
    "悠哉悠哉": "悠哉遊哉",
    "求神拜佛": "燒香拜佛",
    "浪得虛名": "徒有虛名",
    "牛高馬大": "人高馬大",
    "甩皮甩骨": "瘦骨嶙峋",
    "相對密度": "比重",
    "絕代佳人": "絕世佳人",
    "自立自強": "自強自立",
    "重見光明": "重見天日",
    "雲霄飛車": "過山車",
    "不眠不休": "廢寢忘食",
    "反作用力": "反作用",
    "圖書館員": "圖書管理員",
    "安享晚年": "頤養天年",
    "性格不合": "合不來",
    "無線電波": "電波",
    "硝酸甘油": "硝化甘油",
    "一次方程": "一次方程式",
    "獨家新聞": "獨家報導",
    "科學幻想": "科幻",
    "一飽眼福": "大飽眼福",
    "正態分佈": "常態分佈",
    "真刀真槍": "真槍實彈",
    "高音喇叭": "揚聲器",
    "學齡兒童": "學童",
    "平淡無味": "淡而無味",
    "恍若隔世": "恍如隔世",
    "永無休止": "永無止境",
    "活字印刷": "活版印刷",
    "疏忽大意": "粗心大意",
    "縮成一團": "蜷縮",
    "趁虛而入": "乘虛而入",
    "金玉良言": "至理名言",
    "傷風感冒": "感冒",
    "加減乘除": "四則運算",
    "各色各樣": "各式各樣",
    "囂張氣焰": "氣焰囂張",
    "四肢無力": "軟弱無力",
    "測量工具": "量具",
    "繞來繞去": "兜圈子",
    "荷槍實彈": "真槍實彈",
    "表露無遺": "暴露無遺",
    "裝甲部隊": "裝甲兵",
    "貌美如花": "如花似玉",
    "風水先生": "風水師",
    "上層社會": "上流社會",
    "凱旋歸來": "凱旋而歸",
    "勢在必得": "志在必得",
    "卵母細胞": "卵細胞",
    "反式脂肪": "反式脂肪酸",
    "如期完成": "按時完成",
    "滿口答應": "滿口應承",
    "牛肉拉麪": "牛肉麵",
    "衣衫不整": "衣冠不整",
    "鑑賞能力": "鑑賞力",
    "一語中的": "一語破的",
    "上半部分": "上半部",
    "交叉學科": "跨學科",
    "十字街頭": "十字路口",
    "呲牙咧嘴": "齜牙咧嘴",
    "左思右想": "思前想後",
    "操作環境": "作業環境",
    "標準尺寸": "標準規格",
    "毫髮無損": "安然無恙",
    "結婚典禮": "婚禮",
    "臨危不亂": "臨危不懼",
    "自尋死路": "自取滅亡",
    "追根溯源": "追根究底",
    "指手劃腳": "指手畫腳",
    "殺雞儆猴": "殺一儆百",
    "燒香拜佛": "求神拜佛",
    "直接了當": "直截了當",
    "人盡皆知": "眾所周知",
    "化妝舞會": "化裝舞會",
    "揭幕儀式": "揭幕式",
    "泛泛之輩": "平庸之輩",
    "裝瘋賣傻": "裝傻充愣",
    "避而不談": "閉口不談",
    "人口結構": "人口構成",
    "僅作參考": "僅供參考",
    "吸食毒品": "吸毒",
    "大展身手": "大顯身手",
    "巾幗英雄": "女中豪傑",
    "忽隱忽現": "若隱若現",
    "花容月貌": "閉月羞花",
    "阿斯匹林": "阿司匹林",
    "全身麻醉": "全麻",
    "可供參考": "僅供參考",
    "家財萬貫": "腰纏萬貫",
    "狼心狗肺": "蛇蠍心腸",
    "自強自立": "自立自強",
    "自我解嘲": "自嘲",
    "過街天橋": "行人天橋",
    "一閃即逝": "稍縱即逝",
    "二號人物": "二把手",
    "天差地別": "天壤之別",
    "意志消沉": "灰心喪氣",
    "感覺器官": "感官",
    "毫不懷疑": "毫無疑問",
    "亂作一團": "亂成一團",
    "全然不同": "截然不同",
    "同生共死": "生死與共",
    "威風八面": "威風凜凜",
    "春秋時代": "春秋時期",
    "淡而無味": "平淡無味",
    "無縫連接": "無縫接軌",
    "胡編亂造": "憑空捏造",
    "包辦婚姻": "盲婚啞嫁",
    "同聲翻譯": "同聲傳譯",
    "花粉過敏": "花粉症",
    "送貨到家": "送貨上門",
    "鎩羽而歸": "敗興而歸",
    "應付自如": "得心應手",
    "懶懶散散": "懶散",
    "盡其所能": "盡力而為",
    "算術平均": "算術平均數",
    "辦公時間": "上班時間",
    "爭權奪利": "爭名奪利",
    "嚴於律己": "嚴以律己",
    "年終獎金": "花紅",
    "自我檢討": "反省",
    "青銅時代": "青銅器時代",
    "生平簡介": "簡歷",
    "標題新聞": "頭條",
    "風姿綽約": "綽約多姿",
    "混混沌沌": "渾渾噩噩",
}

ALTS: dict[str, list[str]] = {
    "嘔心瀝血": ["煞費苦心", "絞盡腦汁"],
    "感同身受": ["頗有同感"],
    "壯志凌雲": ["意氣風發"],
    "一決高下": ["一決雌雄"],
    "不辭而別": ["不辭而去"],
    "華僑": ["僑胞"],
    "別客氣": ["不用客氣"],
    "人高馬大": ["虎背熊腰"],
    "自強自立": ["自力更生"],
    "廢寢忘食": ["通宵達旦", "夜以繼日"],
    "頤養天年": ["安度晚年"],
    "永無止境": ["沒完沒了", "無休無止"],
    "各式各樣": ["各種各樣", "形形色色"],
    "兜圈子": ["轉彎抹角"],
    "一語破的": ["一針見血", "一語道破"],
    "殺一儆百": ["殺雞嚇猴"],
    "眾所周知": ["家喻戶曉"],
    "化裝舞會": ["假面舞會"],
    "大顯身手": ["大顯神通"],
    "若隱若現": ["時隱時現"],
    "閉月羞花": ["沉魚落雁"],
    "阿司匹林": ["阿斯匹靈"],
    "腰纏萬貫": ["富可敵國"],
    "稍縱即逝": ["轉瞬即逝"],
    "天壤之別": ["天差地遠"],
    "灰心喪氣": ["心灰意冷"],
    "威風凜凜": ["八面威風"],
    "敗興而歸": ["空手而歸"],
    "得心應手": ["遊刃有餘"],
    "盡力而為": ["不遺餘力", "全力以赴"],
    "算術平均數": ["平均數"],
}

PROPER = {
    "古文觀止",
    "薩爾茨堡",
    "北洋水師",
    "泰晤士河",
    "鐵達尼號",
    "河北日報",
    "太僕寺旗",
    "三峽水庫",
    "基尼係數",
    "吉爾吉斯",
    "長孫無忌",
    "康熙字典",
    "孟德斯鳩",
    "神龍汽車",
    "貴妃醉酒",
    "卡爾加里",
    "女媧補天",
    "狂人日記",
    "杜莎夫人",
    "六十四卦",
    "獨立宣言",
    "唯物史觀",
    "孔雀開屏",
}

POLY = {
    "吞雲吐霧",
    "表面文章",
    "一葉知秋",
    "見招拆招",
}

CULTURAL = {
    "閉門造車",
    "附庸風雅",
    "青春永駐",
    "五雷轟頂",
    "千刀萬剮",
    "是非之地",
    "無冕之王",
    "避重就輕",
    "上天入地",
    "以毒攻毒",
    "寸土寸金",
    "有所不知",
    "量體裁衣",
    "頭重腳輕",
    "三姑六婆",
    "不懂裝懂",
    "同歸於盡",
    "嘈喧巴閉",
    "天外來客",
    "孤男寡女",
    "害人不淺",
    "得而復失",
    "捷報頻傳",
    "相形見絀",
    "美中不足",
    "阻頭阻勢",
    "各領風騷",
    "屢敗屢戰",
    "拔刀相助",
    "有夫之婦",
    "無惡不作",
    "病從口入",
    "盲目崇拜",
    "一以貫之",
    "人定勝天",
    "及時行樂",
    "寬衣解帶",
    "就地取材",
    "望其項背",
    "滿城風雨",
    "燙手山芋",
    "玉石俱焚",
    "百年樹人",
    "勿忘國恥",
    "天外有天",
    "如意郎君",
    "投石問路",
    "正反兩面",
    "班門弄斧",
    "紅顏薄命",
    "行俠仗義",
    "趨利避害",
    "一眼望去",
    "五味雜陳",
    "人小鬼大",
    "共處一室",
    "嘖嘖稱奇",
    "照單全收",
    "老有所養",
    "自負盈虧",
    "以點帶面",
    "信仰自由",
    "學無止境",
    "招財進寶",
    "文武百官",
    "本性難移",
    "世風日下",
    "來日方長",
    "往事如風",
    "星火燎原",
    "竹籃打水",
    "縱橫捭闔",
    "血跡斑斑",
    "行萬里路",
    "開張大吉",
    "一問一答",
    "一字之差",
    "一柱擎天",
    "哼哼唧唧",
    "寶刀未老",
    "教學相長",
    "明辨是非",
    "無一倖免",
    "無字天書",
    "無所遁形",
    "狗血淋頭",
    "禍從口出",
    "自問自答",
    "阿貓阿狗",
    "一夫當關",
    "做牛做馬",
    "可大可小",
    "橫刀奪愛",
    "難辭其咎",
    "以德服人",
    "以暴制暴",
    "多勞多得",
    "轉移視線",
    "鷸蚌相爭",
    "一死一傷",
    "七葷八素",
    "乾柴烈火",
    "始亂終棄",
    "手下敗將",
    "把酒言歡",
    "毫無道理",
    "滿腔熱血",
    "義薄雲天",
    "長夜漫漫",
    "一病不起",
    "一腳踢開",
    "上吐下瀉",
    "不見天日",
    "大放厥詞",
    "天造地設",
    "嫌貧愛富",
    "成敗得失",
    "流水無情",
    "無利可圖",
    "相談甚歡",
    "縮頭烏龜",
    "一夜風流",
    "人海戰術",
    "大事化小",
    "大是大非",
    "插科打諢",
    "雖敗猶榮",
    "惡有惡報",
    "福星高照",
    "萬物之靈",
    "高手如雲",
    "何必如此",
    "單刀赴會",
    "四海一家",
    "妙筆生花",
    "強買強賣",
    "慾火焚身",
    "綠草如茵",
    "陷入絕境",
    "不勝酒力",
    "何德何能",
    "孤膽英雄",
    "永結同心",
    "沒大沒小",
    "首開紀錄",
    "一紙空文",
    "相視而笑",
    "精耕細作",
    "不明就裏",
    "誓不罷休",
    "委以重任",
    "江郎才盡",
    "驍勇善戰",
    "裝聾作啞",
    "智勇雙全",
    "歷盡艱辛",
    "機不可失",
    "恩恩愛愛",
    "周遊列國",
    "心胸開闊",
    "有權有勢",
    "浩然正氣",
    "雙重人格",
    "氣宇軒昂",
    "長足進步",
}

OTHER = {
    "價值規律",
    "利益輸送",
    "多模光纖",
    "心理現象",
    "泡沫經濟",
    "細胞組織",
    "結構理論",
    "聚酯樹脂",
    "單模光纖",
    "探明儲量",
    "管道運輸",
    "資不抵債",
    "光學玻璃",
    "內酰胺酶",
    "商業應用",
    "完全兼容",
    "微觀世界",
    "次生災害",
    "垂直搜索",
    "大腹便便",
    "省直管縣",
    "紅衣主教",
    "長途電話",
    "一般原則",
    "大舉進攻",
    "應召女郎",
    "物質獎勵",
    "環氧乙烷",
    "遠洋運輸",
    "免疫應答",
    "封建思想",
    "抽象思維",
    "防禦工事",
    "雌性激素",
    "高等代數",
    "三輪車夫",
    "同名同姓",
    "步調一致",
    "清心寡慾",
    "聚酯纖維",
    "速溶咖啡",
    "兩個文明",
    "苯丙氨酸",
    "面試工作",
    "高速網絡",
    "並行計算",
    "價值標準",
    "善後事宜",
    "四腳朝天",
    "基礎結構",
    "海水養殖",
    "社會正義",
    "社會青年",
    "能量代謝",
    "功率輸出",
    "司法獨立",
    "天體物理",
    "容量分析",
    "平均速度",
    "東方文明",
    "水生動物",
    "神職人員",
    "虛擬環境",
    "通信線路",
    "人生意義",
    "國家銀行",
    "字母順序",
    "技術科學",
    "普通教育",
    "標準組織",
    "武裝鬥爭",
    "歪曲事實",
    "遺傳物質",
    "兒科醫生",
    "公司理財",
    "公平貿易",
    "勞動條件",
    "口齒不清",
    "基礎代謝",
    "數據網絡",
    "混合感染",
    "自由競爭",
    "作業系統",
    "醋酸乙酯",
    "外幣存款",
    "旋轉餐廳",
    "求救信號",
    "遠程導彈",
    "三權分立",
    "動態影像",
    "大病初癒",
    "廣泛影響",
    "萬能鑰匙",
    "傳輸模式",
    "商品價值",
    "嗜血桿菌",
    "希伯來語",
    "抗精神病",
    "普魯卡因",
    "複變函數",
    "黯淡無光",
    "外部連接",
    "思想交流",
    "戀母情結",
    "援助機構",
    "曲折離奇",
    "清倉查庫",
    "草食動物",
    "貧富懸殊",
    "遠程登錄",
    "韓國泡菜",
    "驅逐出境",
    "土耳其語",
    "武術比賽",
    "生態足跡",
    "白色污染",
    "行政效率",
    "二次函數",
    "地殼運動",
    "武術指導",
    "勞資糾紛",
    "犯罪集團",
    "十項全能",
    "大駕光臨",
    "合乎邏輯",
    "無惡不作",
    "導彈系統",
    "聽力理解",
    "電視公司",
    "沒有差別",
    "身負重傷",
    "便民利民",
    "專門人員",
    "膠原纖維",
    "語音信箱",
    "地球大氣",
    "文職人員",
    "登山運動",
    "大寫字母",
}


def pick_tail(head: str, preferred: str, lex: set[str]) -> str | None:
    hn = normalize_literal(head)
    for c in [preferred, *ALTS.get(preferred, [])]:
        n = normalize_literal(c)
        if n and n in lex and n != hn:
            return n
    return None


def main() -> int:
    lex = load_lexicon_literals()
    heads = [
        ln.split("\t")[1]
        for ln in (FIXT / "syn_len4_b05_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
        if ln.strip()
    ]
    assert len(heads) == 500, len(heads)

    accepted: OrderedDict[str, str] = OrderedDict()
    failed: list[tuple[str, str]] = []
    for h, t in RAW.items():
        if h not in heads or t == h:
            continue
        got = pick_tail(h, t, lex)
        if got:
            accepted[h] = got
        else:
            failed.append((h, t))

    ant: set[tuple[str, str]] = set()
    con = sqlite3.connect(str(ROOT / "client" / "public" / "lyrics.db"))
    for a, b in con.execute(
        "select w1.char,w2.char from word_relations r "
        "join words w1 on w1.id=r.word_id join words w2 on w2.id=r.related_id "
        "where r.relation_type='ant'"
    ):
        na, nb = normalize_literal(a), normalize_literal(b)
        if na and nb:
            ant.add(pair_undirected_key(na, nb))
    con.close()
    for p in parse_project_antonyms_tsv(ANT_TSV, require_file=True):
        ant.add(p.canonical_key())
    for h, t in list(accepted.items()):
        if pair_undirected_key(h, t) in ant:
            del accepted[h]
            failed.append((h, t + "#ant"))

    existing = {
        p.canonical_key()
        for p in parse_project_synonyms_tsv(DEFAULT_TSV, membership=lex)
    }
    covered: set[str] = set()
    for a, b in existing:
        covered.add(a)
        covered.add(b)

    seen: set[tuple[str, str]] = set()
    rows: list[tuple[str, str]] = []
    batch_cover: set[str] = set()
    for h, t in accepted.items():
        key = pair_undirected_key(h, t)
        if key in seen or key in existing:
            continue
        seen.add(key)
        rows.append((h, t))
        batch_cover.add(normalize_literal(h))
        batch_cover.add(normalize_literal(t))

    acc = {h for h, _ in rows}
    nn: OrderedDict[str, str] = OrderedDict()
    adq: list[tuple[str, str, str]] = []
    for h in heads:
        if h in acc:
            continue
        nh = normalize_literal(h)
        if nh in covered:
            adq.append((h, "prior project_syn edge covers head", BATCH))
            continue
        if nh in batch_cover:
            adq.append((h, "within-batch undirected syn edge covers head", BATCH))
            continue
        if h in POLY:
            nn[h] = "polysemous_no_stable_sense"
        elif h in PROPER:
            nn[h] = "proper_name_or_deixis"
        elif h in CULTURAL and h not in RAW:
            nn[h] = "cultural_no_binary"
        elif h in OTHER and h not in RAW:
            nn[h] = "other_documented"
        else:
            nn[h] = "no_stable_near_synonym"

    adq_h = {h for h, _, _ in adq}
    for h in heads:
        if h not in acc and h not in nn and h not in adq_h:
            nn[h] = "no_stable_near_synonym"

    assert len(acc) + len(nn) + len(adq_h) == 500, (len(acc), len(nn), len(adq_h))
    assert acc.isdisjoint(nn.keys()) and acc.isdisjoint(adq_h) and set(nn).isdisjoint(adq_h)

    (FIXT / "syn_len4_b05_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b05_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b05_adequate.tsv").write_text(
        "head\tnote\tbatch_id\n"
        + "\n".join(f"{h}\t{n}\t{b}" for h, n, b in adq)
        + "\n",
        encoding="utf-8",
    )
    print(
        {
            "accepted": len(rows),
            "nn": len(nn),
            "adq": len(adq),
            "reasons": dict(Counter(nn.values())),
            "failed_n": len(failed),
            "failed": failed[:20],
            "adq_heads": [h for h, _, _ in adq],
            "default_nn": [h for h, r in nn.items() if r == "no_stable_near_synonym"],
            "accepted_sample": rows[:15],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
