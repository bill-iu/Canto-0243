"""Curate syn_len4 batch-6 fixtures (ranks 2501–3000)."""
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
BATCH = "syn-len4-b06-20260718"

# head -> preferred near-synonym tail (must resolve into lexicon via pick_tail)
RAW: dict[str, str] = {
    "藏污納垢": "藏垢納污",
    "一哄而上": "蜂擁而上",
    "乙型腦炎": "乙腦",
    "偷雞摸狗": "偷偷摸摸",
    "力大無窮": "力大無比",
    "堅決否認": "矢口否認",
    "天色已晚": "夜幕降臨",
    "惰性氣體": "稀有氣體",
    "生死之交": "莫逆之交",
    "重重包圍": "層層包圍",
    "隻手遮天": "一手遮天",
    "不論如何": "無論如何",
    "公共財產": "公產",
    "大聲喊叫": "大喊大叫",
    "撕破臉皮": "撕破臉",
    "死而無憾": "死而無悔",
    "知識寶庫": "知識庫",
    "自動自發": "自覺自願",
    "舊事重提": "重提舊事",
    "軍官學校": "軍校",
    "交通擁擠": "擁擠不堪",
    "大便乾燥": "便秘",
    "心理學系": "心理系",
    "指名道姓": "直呼其名",
    "熱身運動": "熱身",
    "薪火相傳": "薪盡火傳",
    "防護眼鏡": "護目鏡",
    "一展身手": "大顯身手",
    "前後矛盾": "自相矛盾",
    "愛管閒事": "多管閒事",
    "感觸良多": "感慨萬千",
    "了無牽掛": "無牽無掛",
    "命運註定": "命中註定",
    "在此之後": "此後",
    "妙齡女子": "妙齡女郎",
    "幾次三番": "三番四次",
    "瘋言瘋語": "胡言亂語",
    "紅光滿面": "容光煥發",
    "詞不達意": "辭不達意",
    "不論怎樣": "無論如何",
    "名門望族": "名門貴族",
    "四處奔走": "東奔西走",
    "心無雜念": "心無旁騖",
    "開始比賽": "開賽",
    "陳詞濫調": "老生常談",
    "不守信用": "言而無信",
    "不知廉恥": "恬不知恥",
    "不論怎麼": "無論如何",
    "來去自如": "進退自如",
    "城市區域": "市區",
    "外國資本": "外資",
    "始終不變": "始終如一",
    "富貴榮華": "榮華富貴",
    "陰曹地府": "陰間",
    "完整無缺": "完好無缺",
    "心懷不軌": "居心不良",
    "惹人注目": "引人注目",
    "戰死沙場": "陣亡",
    "一國之君": "一國之主",
    "拔腿就跑": "拔足狂奔",
    "神智不清": "神志不清",
    "纖塵不染": "一塵不染",
    "茶飯不思": "茶飯無心",
    "衝口而出": "脫口而出",
    "露出馬腳": "敗露",
    "一片苦心": "一番苦心",
    "三氯甲烷": "氯仿",
    "大氣壓力": "氣壓",
    "直來直往": "直來直去",
    "草草了事": "敷衍了事",
    "裝甲車輛": "裝甲車",
    "飽和狀態": "飽和",
    "如假包換": "貨真價實",
    "實況轉播": "現場直播",
    "目眩神迷": "眼花繚亂",
    "結拜兄弟": "把兄弟",
    "英勇犧牲": "為國捐軀",
    "凌亂不堪": "亂七八糟",
    "日落西山": "日薄西山",
    "水陸兩棲": "兩棲",
    "荒淫無度": "荒淫無道",
    "薩克斯風": "薩克斯管",
    "心術不正": "居心不良",
    "牢記在心": "銘記在心",
    "傳播媒體": "傳媒",
    "小題大作": "小題大做",
    "幾何級數": "等比級數",
    "網絡日記": "網誌",
    "行動電話": "手機",
    "視覺神經": "視神經",
    "一字不漏": "一字不落",
    "千挑萬選": "精挑細選",
    "地痞流氓": "地痞",
    "正正經經": "一本正經",
    "出人意表": "出人意料",
    "化石燃料": "礦物燃料",
    "天才兒童": "神童",
    "機械工人": "機工",
    "疲勞過度": "精疲力竭",
    "絕頂聰明": "聰明絕頂",
    "觀察人士": "觀察員",
    "雜技表演": "雜技",
    "修心養性": "修身養性",
    "同胞兄弟": "親兄弟",
    "喜不自禁": "欣喜若狂",
    "坐視不理": "袖手旁觀",
    "徘徊不前": "裹足不前",
    "知識份子": "知識分子",
    "長生不死": "長生不老",
    "別無他法": "無計可施",
    "化學治療": "化療",
    "大禍臨頭": "大難臨頭",
    "大有希望": "大有可為",
    "引體向上": "引體上升",
    "懸崖絕壁": "懸崖峭壁",
    "皮包公司": "空殼公司",
    "神乎其技": "出神入化",
    "一次能源": "初級能源",
    "婦女運動": "女權運動",
    "經濟落後": "貧窮落後",
    "結婚儀式": "婚禮",
    "惹禍上身": "自找麻煩",
    "既成事實": "木已成舟",
    "面壁思過": "閉門思過",
    "國家預算": "財政預算",
    "總司令部": "司令部",
    "放高利貸": "放債",
    "不可分離": "密不可分",
    "嚴刑拷打": "嚴刑逼供",
    "印象主義": "印象派",
    "液體燃料": "燃油",
    "大發慈悲": "慈悲為懷",
    "所見略同": "不謀而合",
    "收買人心": "籠絡人心",
    "直接選舉": "直選",
    "外層空間": "外太空",
    "日夜兼程": "披星戴月",
    "公開指責": "口誅筆伐",
    "電光石火": "電光火石",
    "三代同堂": "四世同堂",
    "白跑一趟": "徒勞無功",
    "平頭百姓": "老百姓",
    "上古時代": "上古",
    "肢體衝突": "肢體暴力",
    "低筋麪粉": "低筋",
    "大費周章": "煞費苦心",
    "作者不詳": "佚名",
    "絲毫不差": "一模一樣",
    "前途渺茫": "黯淡無光",
    "分身乏術": "應接不暇",
    "外柔內剛": "綿裏藏針",
    "止咳糖漿": "止咳水",
    "品種改良": "育種",
    "面臨困難": "碰到困難",
    "體外受精": "試管嬰兒",
    "偶然事件": "意外",
    "生產過剩": "供過於求",
    "中心內容": "中心思想",
    "基礎問題": "關鍵問題",
    "刻苦努力": "刻苦耐勞",
    "後勤人員": "後勤",
    "貌不驚人": "其貌不揚",
    "獨立精神": "獨立自主",
    "高等植物": "維管束植物",
    "稽查人員": "稽查",
}

ALTS: dict[str, list[str]] = {
    "蜂擁而上": ["一窩蜂"],
    "夜幕降臨": ["暮色蒼茫"],
    "層層包圍": ["團團包圍"],
    "無論如何": ["怎樣也好"],
    "大喊大叫": ["大聲呼叫"],
    "自覺自願": ["自動自覺"],
    "重提舊事": ["舊調重彈"],
    "擁擠不堪": ["車水馬龍"],
    "薪盡火傳": ["世代相傳"],
    "大顯身手": ["大顯神通"],
    "感慨萬千": ["百感交集"],
    "三番四次": ["再三再四"],
    "容光煥發": ["滿面紅光"],
    "東奔西走": ["到處奔走"],
    "陰間": ["地府"],
    "居心不良": ["心懷叵測"],
    "引人注目": ["令人矚目"],
    "陣亡": ["馬革裹屍"],
    "脫口而出": ["冲口而出"],
    "現場直播": ["直播"],
    "眼花繚亂": ["目眩神搖"],
    "把兄弟": ["結義兄弟"],
    "為國捐軀": ["壯烈犧牲"],
    "亂七八糟": ["凌亂不堪"],
    "兩棲": ["兩棲動物"],
    "精疲力竭": ["疲憊不堪"],
    "欣喜若狂": ["喜出望外"],
    "袖手旁觀": ["漠不關心"],
    "裹足不前": ["踟躕不前", "停滯不前"],
    "無計可施": ["別無選擇"],
    "大有可為": ["前程似錦"],
    "空殼公司": ["紙上公司"],
    "出神入化": ["鬼斧神工"],
    "女權運動": ["女權主義"],
    "婚禮": ["結婚典禮"],
    "自找麻煩": ["自取其辱"],
    "財政預算": ["政府預算"],
    "司令部": ["總部"],
    "放債": ["放貸"],
    "嚴刑逼供": ["嚴刑拷問"],
    "燃油": ["燃料"],
    "不謀而合": ["所見略同"],
    "外太空": ["太空"],
    "披星戴月": ["馬不停蹄"],
    "口誅筆伐": ["大加撻伐"],
    "電光火石": ["轉瞬之間"],
    "徒勞無功": ["白費力氣"],
    "老百姓": ["平民"],
    "上古": ["遠古"],
    "煞費苦心": ["費盡心思"],
    "佚名": ["無名氏"],
    "毫無差別": ["一模一樣"],
    "前路茫茫": ["黯淡無光"],
    "應接不暇": ["騰不出手"],
    "主要內容": ["核心內容"],
    "根本問題": ["核心問題"],
    "設計流程": ["設計步驟"],
    "刻苦耐勞": ["勤奮刻苦", "努力不懈"],
    "舊調重彈": ["重提舊事"],
    "體外授精": ["試管嬰兒"],
    "面對困難": ["遭遇困難"],
    "相互監督": ["彼此監督"],
    "聞風而至": ["聞風而動"],
    "信任危機": ["信貸危機"],
    "深入了解": ["加深瞭解"],
}

PROPER = {
    "仰韶文化",
    "拉卜楞寺",
    "平津戰役",
    "國際聯盟",
    "三皇五帝",
    "教育大學",
    "白山黑水",
    "百團大戰",
    "巴山夜雨",
    "彌勒菩薩",
    "薩摩耶犬",
    "達坂城區",
    "龍山文化",
    "西哈努克",
    "國家體委",
    "天主教會",
    "比薩斜塔",
    "瓦努阿圖",
    "亞馬遜河",
    "武王伐紂",
    "夢溪筆談",
    "明十三陵",
    "濟南地區",
    "金華火腿",
    "匈牙利語",
    "隋唐演義",
    "東郭先生",
    "伏爾加河",
    "格里高利",
    "橫斷山脈",
    "物種起源",
    "開曼群島",
    "埃德蒙頓",
    "大日如來",
    "專員公署",
    "翰林學士",
}

POLY = {
    "肌膚之親",
    "戴綠帽子",
    "魚水之歡",
    "美式足球",
}

CULTURAL = {
    "辣手摧花",
    "陰盛陽衰",
    "以柔克剛",
    "守身如玉",
    "老夫少妻",
    "靡靡之音",
    "不進則退",
    "仁者無敵",
    "業精於勤",
    "知行合一",
    "碎屍萬段",
    "血光之災",
    "負荊請罪",
    "一線之隔",
    "假以時日",
    "傾巢而出",
    "夜夜笙歌",
    "政教合一",
    "決勝千里",
    "草菅人命",
    "請多關照",
    "風韻猶存",
    "以少勝多",
    "女士優先",
    "意興闌珊",
    "抓耳撓腮",
    "春心蕩漾",
    "身家性命",
    "不毛之地",
    "人財兩空",
    "因緣際會",
    "後院起火",
    "忽高忽低",
    "明心見性",
    "深居簡出",
    "無米之炊",
    "三從四德",
    "勤勞致富",
    "大材小用",
    "男尊女卑",
    "秋後算賬",
    "迎來送往",
    "青春不再",
    "一箭之仇",
    "亂點鴛鴦",
    "困獸之鬥",
    "引火燒身",
    "沾花惹草",
    "知無不言",
    "跌破眼鏡",
    "包治百病",
    "外強中乾",
    "彈丸之地",
    "紅白喜事",
    "繁文縟節",
    "自報家門",
    "認祖歸宗",
    "不醉不歸",
    "何必當初",
    "友誼萬歲",
    "新婚燕爾",
    "早生貴子",
    "望聞問切",
    "毛手毛腳",
    "物競天擇",
    "長袖善舞",
    "人如其名",
    "天誅地滅",
    "年年有餘",
    "拱手相讓",
    "拿不出手",
    "流年不利",
    "自命清高",
    "九九歸一",
    "出口成章",
    "喪家之犬",
    "屍橫遍野",
    "忠言逆耳",
    "投鼠忌器",
    "殃及池魚",
    "百口莫辯",
    "謀財害命",
    "多難興邦",
    "天打雷劈",
    "捨己救人",
    "時運不濟",
    "珍禽異獸",
    "兵不厭詐",
    "出此下策",
    "千古罪人",
    "善有善報",
    "坦白從寬",
    "思想包袱",
    "毀屍滅跡",
    "藥食同源",
    "軍閥混戰",
    "和氣生財",
    "地主之誼",
    "學富五車",
    "寵愛有加",
    "平心而論",
    "後會有期",
    "花拳繡腿",
    "五福臨門",
    "洞天福地",
    "身首異處",
    "一官半職",
    "一拍兩散",
    "大而化之",
    "楚河漢界",
    "百鳥朝鳳",
    "盡忠職守",
    "只欠東風",
    "大事不妙",
    "委屈求全",
    "五臟俱全",
    "口耳相傳",
    "呼哧呼哧",
    "明月清風",
    "掌聲雷動",
    "聞風而動",
    "大權在握",
    "奪門而出",
}

OTHER = {
    "統一招生",
    "雕樑畫棟",
    "電子貨幣",
    "高檔服裝",
    "有進取心",
    "成語典故",
    "現在分詞",
    "眼科醫生",
    "規定動作",
    "定向越野",
    "常染色體",
    "最小二乘",
    "膽鹼酯酶",
    "胃酸過多",
    "語言訓練",
    "財政危機",
    "轉變過程",
    "中式英語",
    "二氯甲烷",
    "卡布其諾",
    "搜尋引擎",
    "民族資本",
    "物理現象",
    "藏身之處",
    "銀行利息",
    "僵屍網絡",
    "口不擇言",
    "外匯收入",
    "太陽黑子",
    "字正腔圓",
    "意下如何",
    "放下包袱",
    "生命跡象",
    "資產剝離",
    "雞尾酒會",
    "頻率合成",
    "國家制度",
    "天干地支",
    "應付帳款",
    "權利能力",
    "細胞毒性",
    "綜合藝術",
    "迂迴曲折",
    "世界強國",
    "保護模式",
    "刑事判決",
    "十四行詩",
    "工業中心",
    "引水工程",
    "形式邏輯",
    "情緒狀態",
    "武藝高強",
    "江河湖海",
    "直角座標",
    "第二世界",
    "轉移安置",
    "雌雄同體",
    "互相聯繫",
    "保外就醫",
    "固體物理",
    "基本矛盾",
    "外力作用",
    "潺潺流水",
    "有線廣播",
    "網管系統",
    "香甜可口",
    "價值工程",
    "制動踏板",
    "即興表演",
    "君主專制",
    "國家考試",
    "基底動脈",
    "基本粒子",
    "官僚資本",
    "撥號連接",
    "數據總線",
    "油料作物",
    "劃清界線",
    "臨終關懷",
    "一級士官",
    "地方自治",
    "按摩療法",
    "沉船事故",
    "語音合成",
    "金髮女郎",
    "好言相勸",
    "整風運動",
    "知情同意",
    "餘震不斷",
    "中俄關系",
    "人類起源",
    "匍匐前進",
    "四氯乙烯",
    "國家主義",
    "大氣環流",
    "天冬氨酸",
    "教學機構",
    "環保主義",
    "遲到早退",
    "二氧化錳",
    "低空飛行",
    "分組交換",
    "古典藝術",
    "喪失殆盡",
    "地熱資源",
    "庫存現金",
    "消化器官",
    "特此通知",
    "人稱代詞",
    "假性近視",
    "共同市場",
    "利己主義",
    "加工成本",
    "化學平衡",
    "口述歷史",
    "國土安全",
    "壟斷市場",
    "心電感應",
    "有效射程",
    "熱帶氣候",
    "甲型肝炎",
    "粒子物理",
    "軍用機場",
    "旅行支票",
    "空氣阻力",
    "邊際成本",
    "亞硝酸鈉",
    "和平利用",
    "填字遊戲",
    "心臟病發",
    "林可黴素",
    "機械運動",
    "語音信號",
    "象徵主義",
    "一字不差",
    "學術自由",
    "桌面系統",
    "獨立運動",
    "由上而下",
    "肱二頭肌",
    "長途話費",
    "風雨雷電",
    "問題少年",
    "隨時待命",
    "一時糊塗",
    "停戰協定",
    "巍然屹立",
    "滴酒不沾",
    "牙牙學語",
    "加深理解",
    "信用危機",
    "互相監督",
    "設計程序",
    "用餐時間",
    "絡腮鬍子",
    "血汗工廠",
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
        for ln in (FIXT / "syn_len4_b06_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
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

    (FIXT / "syn_len4_b06_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b06_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b06_adequate.tsv").write_text(
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
            "failed": failed[:30],
            "adq_heads": [h for h, _, _ in adq],
            "default_nn": [h for h, r in nn.items() if r == "no_stable_near_synonym"],
            "accepted_sample": rows[:15],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
