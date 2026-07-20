"""Curate syn_len4 batch-2 fixtures (ranks 501–1000)."""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import sqlite3
import sys
from collections import Counter, OrderedDict
from pathlib import Path

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
BATCH = "syn-len4-b02-20260718"

# head -> preferred near-synonym tail (must resolve into lexicon via pick_tail)
RAW: dict[str, str] = {
    "不懷好意": "居心不良",
    "東南西北": "四面八方",
    "標點符號": "標點",
    "節約能源": "節能",
    "勞動模範": "勞模",
    "筋疲力盡": "精疲力竭",
    "退伍軍人": "退役軍人",
    "天下無敵": "所向無敵",
    "不得其解": "大惑不解",
    "泣不成聲": "痛哭失聲",
    "慈善機構": "慈善團體",
    "利益衝突": "利害衝突",
    "初戀情人": "初戀",
    "手提電腦": "筆記本電腦",
    "機動車輛": "機動車",
    "專科學校": "專科",
    "木馬病毒": "木馬",
    "私有財產": "私產",
    "四方八面": "四面八方",
    "如此一來": "這樣一來",
    "聽唔入耳": "聽不進去",
    "閃閃縮縮": "畏畏縮縮",
    "軍事訓練": "軍訓",
    "一聲不吭": "一言不發",
    "定期存款": "定期儲蓄",
    "憤憤不平": "忿忿不平",
    "遮遮掩掩": "躲躲閃閃",
    "不用客氣": "不客氣",
    "日常用品": "日用品",
    "信用等級": "信用評級",
    "手足口病": "手足口症",
    "新生事物": "新事物",
    "貪污受賄": "貪贓枉法",
    "國營企業": "國企",
    "毛絨玩具": "毛公仔",
    "文具用品": "文具",
    "暗箱操作": "黑箱操作",
    "再生能源": "可再生能源",
    "突然之間": "忽然之間",
    "使用手冊": "使用説明",
    "心肌梗死": "心肌梗塞",
    "會議展覽": "會展",
    "家庭教師": "補習老師",
    "世界貿易": "國際貿易",
    "開學典禮": "開學禮",
    "優惠價格": "優惠價",
    "同聲傳譯": "即時傳譯",
    "網頁地址": "網址",
    "通信網絡": "通信網",
    "知心朋友": "知己",
    "三番四次": "三番五次",
    "大大話話": "誇誇其談",
    "支吾以對": "支吾其詞",
    "無聲無息": "悄無聲息",
    "真真正正": "真正",
    "陸陸續續": "陸續",
    "電視直播": "直播",
    "吸取教訓": "汲取教訓",
    "渾身上下": "全身上下",
    "中秋佳節": "中秋節",
    "基因工程": "遺傳工程",
    "一時之間": "一時",
    "水力發電": "水電",
    "簡要介紹": "簡介",
    "量身定製": "度身訂造",
    "評審委員": "評委",
    "中心地帶": "中心區",
    "年紀輕輕": "年少",
    "心地善良": "心地好",
    "百貨商場": "百貨公司",
    "地球科學": "地學",
    "傷心欲絕": "痛不欲生",
    "放射治療": "放療",
    "恐怖電影": "恐怖片",
    "吵吵鬧鬧": "吵鬧",
    "乾淨利落": "乾淨俐落",
    "帶狀皰疹": "生蛇",
    "故意殺人": "謀殺",
    "健康檢查": "體檢",
    "選秀節目": "選秀",
    "一片漆黑": "漆黑一團",
    "從現在起": "從今以後",
    "健身運動": "健身",
    "內幕交易": "內線交易",
    "援助之手": "援手",
    "猝不及防": "措手不及",
    "質量檢查": "品質檢查",
    "植物保護": "植保",
    "電化教育": "電化教學",
    "周而復始": "週而復始",
    "中國醫藥": "中醫藥",
    "精神分裂": "思覺失調",
    "有機玻璃": "亞克力",
    "人流手術": "人工流產",
    "瑟瑟發抖": "顫抖",
    "家庭作業": "功課",
    "致癌物質": "致癌物",
    "尋人啓事": "尋人啟事",
    "直系親屬": "直系血親",
    "健健康康": "健康",
}

ALTS: dict[str, list[str]] = {
    "筆記本電腦": ["筆記型電腦"],
    "四面八方": ["四方八面"],
    "信用評級": ["信用等級"],
    "忽然之間": ["突然之間"],
    "全身上下": ["渾身上下"],
    "使用説明": ["使用說明"],
    "國際貿易": ["世界貿易"],
    "痛不欲生": ["肝腸寸斷"],
    "乾淨俐落": ["乾淨利落"],
    "尋人啟事": ["尋人啓事"],
}

# proper names / brands / titles / orgs / geo
PROPER = {
    "黑客帝國",
    "科特迪瓦",
    "烏蘭察布",
    "新聞週刊",
    "牛郎織女",
    "俠盜飛車",
    "馬可波羅",
    "銅仁地區",
    "二十一條",
    "春秋戰國",
    "天線寶寶",
    "五四運動",
    "古墓麗影",
    "龍門石窟",
    "德克薩斯",
    "齊天大聖",
    "瑞士軍刀",
    "兩岸三地",
    "菲尼克斯",
    "提拉米蘇",
    "南沙羣島",
    "音樂之聲",
    "波西米亞",
    "五大連池",
    "四大名著",
    "聊齋志異",
    "參考消息",
    "超級女生",
    "八國聯軍",
    "第一夫人",
    "馬列主義",
}

# opaque cultural / idiom with no stable binary near-syn
CULTURAL = {
    "不懷好意",  # in RAW
    "喜新厭舊",
    "天下無敵",  # in RAW
    "閃閃發光",
    "審美疲勞",
    "行雲流水",
    "輕鬆愉快",
    "重出江湖",
    "有感而發",
    "用武之地",
    "優勝劣汰",
    "泣不成聲",  # in RAW
    "一脈相承",
    "初來乍到",
    "嶄露頭角",
    "走馬觀花",
    "生不如死",
    "樂在其中",
    "若即若離",
    "侃侃而談",
    "周而復始",  # in RAW
    "生生不息",
    "用心良苦",
    "糾纏不清",
    "品學兼優",
    "水土不服",
    "憂患意識",
    "性情中人",
    "逢年過節",
    "色即是空",
    "不失時機",
    "一聲不吭",  # in RAW
    "當家作主",
    "憤憤不平",  # in RAW
    "衣食無憂",
    "晃晃悠悠",
    "遮遮掩掩",  # in RAW
    "不得好死",
    "自生自滅",
    "遍地開花",
    "另當別論",
    "崇洋媚外",
    "打情罵俏",
    "仁者見仁",
    "忍辱負重",
    "一言難盡",
    "以身相許",
    "勞逸結合",
    "百獸之王",
    "誤人子弟",
    "禽獸不如",
    "與生俱來",
    "漸行漸遠",
    "上綱上線",
    "不可收拾",
    "毫無保留",
    "柳暗花明",
    "生生世世",
    "兩敗俱傷",
    "春意盎然",
    "一夜之間",
    "一手一腳",
    "一閃而過",
    "口口聲聲",
    "古靈精怪",
    "大大話話",  # in RAW
    "山雨欲來",
    "從長計議",
    "支吾以對",  # in RAW
    "無聲無息",  # in RAW
    "見死不救",
    "順其自然",
    "中規中矩",
    "高山流水",
    "養生之道",
    "一分一秒",
    "物超所值",
    "不惜一切",
    "冥冥之中",
    "疑難雜症",
    "山盟海誓",
    "流光溢彩",
    "面面相覷",
    "若有若無",
    "雲淡風輕",
    "百家爭鳴",
    "兵臨城下",
    "海納百川",
    "童言無忌",
    "細細品味",
    "觸手可及",
    "驀然回首",
    "蝴蝶效應",
    "一念之間",
    "後知後覺",
    "樂於助人",
    "隻言片語",
    "縱橫天下",
    "單身貴族",
    "尋尋覓覓",
    "飛蛾撲火",
    "全副武裝",
    "失而復得",
    "鳥語花香",
    "未完待續",
    "開花結果",
    "一臂之力",
    "永無止境",
    "不知疲倦",
    "傷心欲絕",  # in RAW
    "怦然心動",
    "曲終人散",
    "交相輝映",
    "君臨天下",
    "惺惺相惜",
    "立於不敗",
    "開天闢地",
    "萬家燈火",
    "藍顏知己",
    "不見不散",
    "全身而退",
    "三言兩語",
    "將計就計",
    "燈火通明",
    "夕陽西下",
    "時光倒流",
    "機緣巧合",
    "滿心歡喜",
    "何時何地",
    "帽子戲法",
    "心如止水",
    "更勝一籌",
    "大放異彩",
    "從無到有",
    "朝九晚五",
    "猝不及防",  # in RAW
    "琴棋書畫",
    "生意興隆",
    "人生在世",
    "意亂情迷",
    "拔地而起",
    "鬼使神差",
    "黯然失色",
    "七情六慾",
    "五官端正",
    "半信半疑",
    "川流不息",
    "打起精神",
    "熱氣騰騰",
    "瑟瑟發抖",  # in RAW
    "血肉模糊",
    "返璞歸真",
    "人間仙境",
    "一飲而盡",
    "呼嘯而過",
    "強身健體",
    "生存之道",
    "真命天子",
    "一個勁兒",
    "因材施教",
    "大喝一聲",
    "弱肉強食",
    "揚長而去",
    "放聲大哭",
    "筋疲力盡",  # in RAW
    "不得其解",  # in RAW
}

# legal / boilerplate / slogan / opaque technical compounds
OTHER = {
    "優先發展",
    "光合作用",
    "男女平等",
    "互相幫助",
    "出版日期",
    "教育制度",
    "不可抗力",
    "來電顯示",
    "功能模塊",
    "副總經理",
    "自我介紹",
    "上皮細胞",
    "國際新聞",
    "心理因素",
    "個人主義",
    "環保意識",
    "出門在外",
    "隱私政策",
    "民主監督",
    "國家權力",
    "恐怖組織",
    "食慾不振",
    "從頭開始",
    "種族歧視",
    "頭等大事",
    "家庭主婦",
    "業務水平",
    "經濟作物",
    "內心深處",
    "公共事務",
    "發明創造",
    "國計民生",
    "消費習慣",
    "特異功能",
    "科學精神",
    "總體目標",
    "成人教育",
    "圖形界面",
    "人文社科",
    "環氧樹脂",
    "電子工程",
    "接觸不良",
    "先進水平",
    "比較分析",
    "國內生產",
    "自我評價",
    "面對現實",
    "週邊設備",
    "玻璃纖維",
    "腰椎間盤",
    "現代文學",
    "信號處理",
    "軟件技術",
    "世界文化",
    "模擬考試",
    "四門轎車",
    "電子工業",
    "全文檢索",
    "失物招領",
    "抑制作用",
    "特約記者",
    "權利聲明",
    "民主生活",
    "生日蛋糕",
    "流動資產",
    "視頻點播",
    "辦公地址",
    "生涯規劃",
    "教學大綱",
    "通訊設備",
    "參考價值",
    "臨牀經驗",
    "自我安慰",
    "耳鼻喉科",
    "學位證書",
    "離子交換",
    "設計規範",
    "國家公園",
    "新鮮空氣",
    "紡織工業",
    "一年一度",
    "冶金工業",
    "私家偵探",
    "人身保險",
    "手拉葫蘆",
    "歷史沿革",
    "一房一廳",
    "兒童教育",
    "深刻印象",
    "細胞因子",
    "另行通知",
    "生活空間",
    "長大成人",
    "靈魂深處",
    "副董事長",
    "滾子軸承",
    "生活設施",
    "耳鼻咽喉",
    "遠程監控",
    "生活污水",
    "勞動能力",
    "學習計劃",
    "文字處理",
    "珍珠奶茶",
    "生殖器官",
    "絕緣材料",
    "有氧運動",
    "顧問公司",
    "專家評論",
    "故障排除",
    "千萬富翁",
    "專欄作家",
    "微觀經濟",
    "快樂幸福",
    "數據通信",
    "熱帶植物",
    "高脂血症",
    "一千零一",
    "從頭到腳",
    "經濟週期",
    "貿易組織",
    "商業計劃",
    "讓人羨慕",
    "通信地址",
    "電源開關",
    "勞動保護",
    "結締組織",
    "外科醫生",
    "旋轉木馬",
    "業餘愛好",
    "沙灘排球",
    "壓縮空氣",
    "精密儀器",
    "醉酒駕車",
    "電解電容",
    "人機界面",
    "專家系統",
    "極限運動",
    "第一人稱",
    "血栓形成",
    "遊戲設備",
    "報刊雜誌",
    "專題報告",
    "工業學校",
    "自由職業",
    "不受歡迎",
    "先後順序",
    "東方文化",
    "空氣動力",
    "傳統教育",
    "生物降解",
    "精神財富",
    "行政拘留",
    "逃避現實",
    "外部鏈接",
    "職業素質",
    "鋼鐵工業",
    "國立大學",
    "跨海大橋",
    "下班時間",
    "世界地圖",
    "中秋月餅",
    "自由市場",
    "花草樹木",
    "全校師生",
    "崗位培訓",
    "課外活動",
    "電子電路",
    "基因突變",
    "巨噬細胞",
    "打打鬧鬧",
    "未解之謎",
    "武裝分子",
    "電子器件",
    "化學分析",
    "搶險救災",
    "生物質能",
    "親密關係",
    "通信服務",
    "醫學檢驗",
    "信用評級",  # covered via RAW 信用等級; if RAW fails → other
    "國民收入",
    "技術知識",
    "旅遊集散",
    "網絡協議",
    "議事規則",
    "鮮明對比",
    "儲蓄銀行",
    "打高爾夫",
    "推卸責任",
    "百科詞典",
    "視覺藝術",
    "音頻文件",
    "移動設備",
    "精神面貌",
    "換位思考",
    "辦事機構",
    "公職人員",
    "退休年齡",
    "儲蓄存款",
    "地心吸力",
    "電視頻道",
    "火山爆發",
    "同母異父",
    "昏昏沉沉",
    "同等學力",
    "家用電腦",
    "電氣工程",
    "天然橡膠",
}

POLY: set[str] = set()


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
        for ln in (FIXT / "syn_len4_b02_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
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

    (FIXT / "syn_len4_b02_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b02_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b02_adequate.tsv").write_text(
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
            "accepted_sample": rows[:15],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
