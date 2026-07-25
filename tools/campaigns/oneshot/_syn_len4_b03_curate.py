"""Curate syn_len4 batch-3 fixtures (ranks 1001–1500)."""
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
BATCH = "syn-len4-b03-20260718"

# head -> preferred near-synonym tail (must resolve into lexicon via pick_tail)
RAW: dict[str, str] = {
    "學生運動": "學運",
    "程序控制": "程控",
    "雙管齊下": "左右開弓",
    "國外市場": "國際市場",
    "神清氣爽": "精神爽利",
    "道德品質": "品德",
    "無可避免": "不可避免",
    "簡單明瞭": "淺顯易懂",
    "絮絮叨叨": "嘮嘮叨叨",
    "軍事委員": "軍委",
    "呼呼大睡": "酣睡",
    "眼皮底下": "眼底下",
    "言行舉止": "言談舉止",
    "節約用水": "節水",
    "真心真意": "真心實意",
    "通貨緊縮": "通縮",
    "帕金森病": "柏金遜症",
    "無路可走": "走投無路",
    "多管閒事": "好管閒事",
    "自下而上": "由下而上",
    "不理不睬": "置之不理",
    "前後左右": "四周",
    "另闢蹊徑": "獨闢蹊徑",
    "瘋瘋癲癲": "瘋癲",
    "國內貿易": "內貿",
    "思維敏捷": "思路敏捷",
    "費盡心思": "費盡心機",
    "投案自首": "自首",
    "數據接口": "數據介面",
    "有聲讀物": "有聲書",
    "一線希望": "一線生機",
    "女權主義": "女性主義",
    "止跌回升": "止跌回穩",
    "空空蕩蕩": "空蕩蕩",
    "一時半會": "一時半刻",
    "四處張望": "東張西望",
    "活期存款": "活期儲蓄",
    "五筆字型": "五筆字形",
    "單打獨鬥": "單槍匹馬",
    "愛理不理": "愛答不理",
    "電影明星": "影星",
    "氣象預報": "天氣預報",
    "精雕細琢": "精雕細刻",
    "人工授精": "人工受精",
    "化學纖維": "化纖",
    "水路運輸": "水運",
    "辨證論治": "辨證施治",
    "枯燥無味": "枯燥乏味",
    "齊頭並進": "並駕齊驅",
    "傳動裝置": "傳動機構",
    "公共廁所": "公廁",
    "收支平衡": "收支相抵",
    "最後通牒": "哀的美敦書",
    "窮追不捨": "窮追猛打",
    "習慣用語": "慣用語",
    "閒言碎語": "閒言閒語",
    "公務人員": "公務員",
    "將信將疑": "半信半疑",
    "穿着打扮": "衣著打扮",
    "精神飽滿": "精神奕奕",
    "大量生產": "量產",
    "得力助手": "左右手",
    "難以相信": "難以置信",
    "不藥而癒": "不治而癒",
    "心裏有數": "心中有數",
    "精神失常": "精神錯亂",
    "面帶笑容": "面帶微笑",
    "一夫一妻": "一夫一妻制",
    "三國鼎立": "三足鼎立",
    "轉眼之間": "轉瞬間",
    "體格檢查": "體檢",
    "便利商店": "便利店",
    "臨牀實驗": "臨牀試驗",
    "雞飛狗跳": "雞飛狗走",
    "公立學校": "官立學校",
    "高等法院": "高院",
    "十六進制": "十六進位",
    "非比尋常": "不同尋常",
    "切實有效": "行之有效",
    "付諸行動": "付諸實施",
    "良苦用心": "用心良苦",
    "全體師生": "全校師生",
    "隨叫隨到": "隨傳隨到",
    "人文科學": "人文學科",
    "風流倜儻": "風流瀟灑",
    "一錯再錯": "一誤再誤",
    "美夢成真": "夢想成真",
    "渾水摸魚": "混水摸魚",
    "白頭到老": "白頭偕老",
    "活力四射": "生氣勃勃",
    "各懷鬼胎": "心懷鬼胎",
    "高人一等": "勝人一籌",
    "故地重遊": "舊地重遊",
    "大徹大悟": "恍然大悟",
    "一面之緣": "一面之交",
    "神出鬼沒": "出沒無常",
    "轟動一時": "風靡一時",
    "威逼利誘": "軟硬兼施",
    "氣定神閒": "泰然自若",
    "財源滾滾": "財源廣進",
    "一箭雙鵰": "一石二鳥",
    "逃出生天": "死裏逃生",
    "來歷不明": "來路不明",
    "時光飛逝": "光陰似箭",
    "大富大貴": "榮華富貴",
    "昂首挺胸": "昂首闊步",
    "國防工業": "軍工",
    "國家元首": "元首",
    "世界市場": "國際市場",
    "不可戰勝": "戰無不勝",
    "陰晴不定": "喜怒無常",
    "獨來獨往": "獨往獨來",
    "領銜主演": "主演",
    "五穀雜糧": "雜糧",
}

ALTS: dict[str, list[str]] = {
    "不可避免": ["在所難免"],
    "淺顯易懂": ["通俗易懂"],
    "嘮嘮叨叨": ["喋喋不休"],
    "走投無路": ["山窮水盡"],
    "置之不理": ["不聞不問"],
    "東張西望": ["左顧右盼"],
    "五筆字形": ["五筆"],
    "精雕細刻": ["精雕細鏤"],
    "精神奕奕": ["神采奕奕"],
    "心中有數": ["胸有成竹"],
    "體檢": ["健康檢查"],
    "便利店": ["超商"],
    "臨牀試驗": ["臨床試驗"],
    "雞飛狗走": ["雞犬不寧"],
    "行之有效": ["卓有成效"],
    "死裏逃生": ["死裡逃生"],
    "勝人一籌": ["更勝一籌"],
    "公務員": ["公職人員"],
    "數據介面": ["資料介面"],
}

PROPER = {
    "玉皇大帝",
    "亂世佳人",
    "戰國時代",
    "世貿中心",
    "林芝地區",
    "六道輪迴",
    "憨豆先生",
    "阿特拉斯",
    "奇門遁甲",
    "七十二變",
    "胡志明市",
    "諸子百家",
    "西沙群島",
    "阿奇黴素",
    "宮保雞丁",
    "芝士蛋糕",
    "額爾古納",
    "塔城地區",
    "文革時期",
    "淮海戰役",
    "翁牛特旗",
    "王母娘娘",
    "堂吉訶德",
    "經合組織",
    "滿漢全席",
    "四大美女",
    "旅順口區",
    "基地組織",
    "秦始皇陵",
    "冰糖葫蘆",
    "白衣天使",
    "金童玉女",
    "武漢地區",
}

CULTURAL = {
    "學以致用",
    "水天一色",
    "返老還童",
    "千呼萬喚",
    "渾身解數",
    "男扮女裝",
    "組合而成",
    "自導自演",
    "親臨現場",
    "風雨欲來",
    "一統天下",
    "夜幕降臨",
    "大受歡迎",
    "小鳥依人",
    "秋高氣爽",
    "九霄雲外",
    "和平共處",
    "大失所望",
    "大家閨秀",
    "展望未來",
    "時刻準備",
    "深入探討",
    "移情別戀",
    "冰山一角",
    "四處尋找",
    "德才兼備",
    "低俗之風",
    "初露鋒芒",
    "後起之秀",
    "趨之若鶩",
    "而立之年",
    "女扮男裝",
    "渾然天成",
    "自作聰明",
    "上山下鄉",
    "必然結果",
    "饒有興趣",
    "齊聚一堂",
    "判若兩人",
    "咫尺天涯",
    "品味生活",
    "日久生情",
    "獨當一面",
    "真情流露",
    "苦心經營",
    "金光閃閃",
    "書香門第",
    "朝朝暮暮",
    "涉世未深",
    "濃墨重彩",
    "各取所需",
    "歡喜冤家",
    "金戈鐵馬",
    "世態炎涼",
    "新新人類",
    "無藥可救",
    "誤打誤撞",
    "重男輕女",
    "難以捉摸",
    "七年之癢",
    "切合實際",
    "四世同堂",
    "奪眶而出",
    "實至名歸",
    "深藏不露",
    "清澈見底",
    "請勿打擾",
    "鬧中取靜",
    "再好不過",
    "大開殺戒",
    "打定主意",
    "打道回府",
    "月黑風高",
    "無處可逃",
    "陰魂不散",
    "人間天堂",
    "塵土飛揚",
    "如意算盤",
    "形同陌路",
    "明智之舉",
    "難以形容",
    "養育之恩",
    "驚險刺激",
    "含苞待放",
    "多事之秋",
    "如詩如畫",
    "玉樹臨風",
    "落葉歸根",
    "飲食男女",
    "不可侵犯",
    "人生如夢",
    "你來我往",
    "團團圍住",
    "天賜良緣",
    "過關斬將",
    "到此一遊",
    "口乾舌燥",
    "回眸一笑",
    "血濃於水",
    "不吐不快",
    "恍恍惚惚",
    "擦亮眼睛",
    "升官發財",
    "喜極而泣",
    "投懷送抱",
    "星星之火",
    "殺人滅口",
    "牽線搭橋",
    "甜甜蜜蜜",
    "約定俗成",
    "自相殘殺",
    "驚鴻一瞥",
    "不可逾越",
    "事不關己",
    "供過於求",
    "依山傍水",
    "先到先得",
    "含糊不清",
    "天地萬物",
    "時過境遷",
    "流於形式",
    "男兒本色",
    "護花使者",
    "身外之物",
    "適者生存",
    "一瘸一拐",
    "時好時壞",
    "熱情奔放",
    "生辰八字",
    "秀色可餐",
    "自由落體",
    "親眼所見",
    "躡手躡腳",
    "以貌取人",
    "出水芙蓉",
    "必死無疑",
    "志在必得",
    "情何以堪",
    "爭強好勝",
    "男歡女愛",
    "白裏透紅",
    "經歷風雨",
    "良心發現",
    "閉目養神",
    "點睛之筆",
    "受騙上當",
    "囊中羞澀",
    "苦苦哀求",
    "隨地吐痰",
    "大魚大肉",
    "按兵不動",
    "未嘗不可",
    "槍林彈雨",
    "沉默是金",
    "稱兄道弟",
    "自掏腰包",
    "虛張聲勢",
    "行動不便",
    "連綿不絕",
    "隨時歡迎",
    "名利雙收",
    "吹灰之力",
    "蕾絲花邊",
    "蚊蟲叮咬",
    "身經百戰",
    "逆流而上",
    "韜光養晦",
    "冬暖夏涼",
    "嚴正聲明",
    "崢嶸歲月",
    "成語接龍",
    "欲購從速",
    "相夫教子",
    "逐鹿中原",
    "難以解決",
    "像模像樣",
    "周遊世界",
    "官商勾結",
    "戰火紛飛",
    "拾金不昧",
    "有容乃大",
    "每週一次",
    "無法替代",
    "一波又起",
    "一波未平",
    "不解風情",
    "公平合理",
    "前塵往事",
    "啞然失笑",
    "心高氣傲",
    "添磚加瓦",
    "牢獄之災",
    "週末愉快",
    "雙方同意",
    "何年何月",
    "富家子弟",
    "無師自通",
    "可憐巴巴",
    "千金小姐",
    "豪言壯語",
    "顧客至上",
    "文房四寶",
    "久別重逢",
    "油鹽醬醋",
    "精力旺盛",
    "革命先烈",
}

OTHER = {
    "預防接種",
    "體外循環",
    "統一規劃",
    "親筆簽名",
    "分子結構",
    "試管嬰兒",
    "運行狀況",
    "電力工業",
    "技術移民",
    "教育電視",
    "水利樞紐",
    "製藥企業",
    "詩詞歌賦",
    "投票表決",
    "矯形外科",
    "可視電話",
    "特派記者",
    "血吸蟲病",
    "司法制度",
    "專業教育",
    "細胞培養",
    "示範單位",
    "第二產業",
    "維持秩序",
    "人體解剖",
    "文學評論",
    "百歲老人",
    "課外輔導",
    "革命戰爭",
    "最低限度",
    "模擬信號",
    "生態平衡",
    "多種經營",
    "球墨鑄鐵",
    "生日派對",
    "萬有引力",
    "逆反心理",
    "電腦病毒",
    "地方法院",
    "孿生兄弟",
    "番茄紅素",
    "質量保障",
    "半胱氨酸",
    "國家機密",
    "組織生活",
    "救命恩人",
    "統一發票",
    "良性腫瘤",
    "讀寫能力",
    "面色蒼白",
    "合成橡膠",
    "書面許可",
    "至理名言",
    "三房二廳",
    "傳輸距離",
    "會計科目",
    "生物燃料",
    "電力機車",
    "電影劇本",
    "丙烯酸酯",
    "動態網頁",
    "太空行走",
    "國會議員",
    "遊牧民族",
    "季風氣候",
    "手扳葫蘆",
    "氧化作用",
    "網絡成癮",
    "親子關係",
    "五年計劃",
    "價值判斷",
    "數值分析",
    "有機合成",
    "知識青年",
    "積壓物資",
    "路由協議",
    "公共行政",
    "出生缺陷",
    "外交關係",
    "電子文件",
    "電子警察",
    "革命委員",
    "刻苦學習",
    "子宮頸癌",
    "物質財富",
    "疑難解答",
    "皰疹病毒",
    "結業證書",
    "美容手術",
    "語音識別",
    "人體器官",
    "文藝作品",
    "第三人稱",
    "總指揮部",
    "總政治部",
    "邊遠地區",
    "電視廣播",
    "中英對照",
    "地緣政治",
    "外籍人士",
    "權利要求",
    "歷史版本",
    "程控電話",
    "首席代表",
    "公共秩序",
    "國際音標",
    "數學物理",
    "結算方式",
    "運行方式",
    "屋頂花園",
    "第一產業",
    "高速緩存",
    "親生父母",
    "前列腺素",
    "勞動教養",
    "幸福家庭",
    "感性認識",
    "文明社會",
    "朝陽產業",
    "網絡設計",
    "總領事館",
    "人格分裂",
    "公司會議",
    "所屬單位",
    "法治建設",
    "細胞週期",
    "野生植物",
    "開閉幕式",
    "基本國策",
    "客觀世界",
    "機會成本",
    "精神領袖",
    "艾滋病毒",
    "國際公約",
    "惡意代碼",
    "水生植物",
    "現場會議",
    "紅頭文件",
    "齒輪傳動",
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
        for ln in (FIXT / "syn_len4_b03_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
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

    (FIXT / "syn_len4_b03_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b03_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b03_adequate.tsv").write_text(
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
