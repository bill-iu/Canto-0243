"""Curate syn_len4 batch-4 fixtures (ranks 1501–2000)."""
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
BATCH = "syn-len4-b04-20260718"

# head -> preferred near-synonym tail (must resolve into lexicon via pick_tail)
RAW: dict[str, str] = {
    "單純皰疹": "皰疹",
    "武警戰士": "武警",
    "自助餐廳": "自助餐",
    "出土文物": "古物",
    "數字通信": "數據通信",
    "立足之地": "立錐之地",
    "長途旅行": "長途跋涉",
    "麻醉藥品": "麻醉藥",
    "口無遮攔": "口沒遮攔",
    "搶先一步": "捷足先登",
    "明日之星": "新星",
    "穩扎穩打": "穩紮穩打",
    "遠大理想": "崇高理想",
    "參考手冊": "使用手冊",
    "核心人物": "中心人物",
    "水火不容": "勢不兩立",
    "生死關頭": "危急關頭",
    "驚歎不已": "讚歎不已",
    "全然不知": "一無所知",
    "十之八九": "十有八九",
    "專業精神": "敬業精神",
    "扭轉乾坤": "力挽狂瀾",
    "招人喜歡": "討人喜歡",
    "不堪忍受": "忍無可忍",
    "名符其實": "名副其實",
    "太平盛世": "盛世",
    "失血過多": "大出血",
    "爵士音樂": "爵士樂",
    "課外讀物": "課外書",
    "農曆新年": "春節",
    "駕駛執照": "駕照",
    "噪聲污染": "噪音污染",
    "科學普及": "科普",
    "跌打損傷": "跌打",
    "迴光返照": "回光反照",
    "不能自已": "情不自禁",
    "國家機構": "國家機關",
    "完美無瑕": "完美無缺",
    "西班牙文": "西班牙語",
    "雙目失明": "失明",
    "專職人員": "專職",
    "添油加醋": "加油添醋",
    "產前檢查": "產檢",
    "發財致富": "致富",
    "真假難辨": "真偽莫辨",
    "立法機關": "議會",
    "碳酸氫鈉": "蘇打粉",
    "衣衫襤褸": "衣不蔽體",
    "遊行示威": "示威遊行",
    "一直往前": "勇往直前",
    "交通意外": "交通事故",
    "小兒麻痹": "小兒麻痺",
    "新來乍到": "初來乍到",
    "無休無止": "沒完沒了",
    "登門拜訪": "登門造訪",
    "等一會兒": "稍等",
    "左右搖擺": "搖擺不定",
    "張燈結綵": "張燈結彩",
    "核反應堆": "反應堆",
    "武裝警察": "武警",
    "虛度光陰": "蹉跎歲月",
    "傳播媒介": "傳媒",
    "懷恨在心": "記恨",
    "毫無用處": "一無是處",
    "全心投入": "全力以赴",
    "口齒伶俐": "能言善辯",
    "志趣相投": "志同道合",
    "熱帶地區": "熱帶",
    "有軌電車": "電車",
    "結婚證書": "婚書",
    "自卑心理": "自卑感",
    "隻字不提": "隻字未提",
    "鼓舞人心": "振奮人心",
    "孩提時代": "童年",
    "心無旁騖": "專心致志",
    "心胸狹窄": "心胸狹隘",
    "第二職業": "兼職",
    "著名人物": "知名人士",
    "超級鏈接": "超連結",
    "重新做人": "改過自新",
    "至始至終": "自始至終",
    "親屬關係": "親戚關係",
    "不同以往": "今非昔比",
    "歷史遺跡": "古跡",
    "不分晝夜": "夜以繼日",
    "不言自明": "不言而喻",
    "寧缺毋濫": "寧缺勿濫",
    "年老體弱": "年老體衰",
    "有備無患": "防患未然",
    "自然選擇": "天擇",
    "觸摸屏幕": "觸摸屏",
    "重整旗鼓": "重振旗鼓",
    "人工受孕": "人工受精",
    "特寫鏡頭": "特寫",
    "稀土金屬": "稀土",
    "美侖美奐": "美輪美奐",
    "證據確鑿": "鐵證如山",
    "變化莫測": "變幻莫測",
    "不勝感激": "感激不盡",
    "民間舞蹈": "民族舞蹈",
    "得償所願": "如願以償",
    "相差不多": "差不多",
    "知書達理": "知書識禮",
    "駐車制動": "手剎車",
    "得來不易": "來之不易",
    "暗度陳倉": "暗渡陳倉",
    "著稱於世": "聞名遐邇",
    "血管硬化": "動脈硬化",
}

ALTS: dict[str, list[str]] = {
    "口沒遮攔": ["信口開河"],
    "危急關頭": ["生死攸關"],
    "讚歎不已": ["驚嘆不已"],
    "一無所知": ["毫不知情"],
    "忍無可忍": ["無可奈何"],
    "盛世": ["治世"],
    "駕照": ["駕駛證"],
    "交通事故": ["車禍"],
    "小兒麻痺": ["小兒麻痹症"],
    "登門造訪": ["登門"],
    "搖擺不定": ["猶豫不決"],
    "傳媒": ["傳播媒體"],
    "一無是處": ["毫無價值"],
    "全力以赴": ["全心全意"],
    "隻字未提": ["一字不提"],
    "振奮人心": ["激動人心"],
    "專心致志": ["一心一意"],
    "超連結": ["超鏈接"],
    "親戚關係": ["親屬"],
    "古跡": ["古蹟"],
    "夜以繼日": ["日以繼夜"],
    "天擇": ["物競天擇"],
    "觸摸屏": ["觸控螢幕"],
    "人工受精": ["體外受精"],
    "變幻莫測": ["變化無常"],
    "感激不盡": ["萬分感激"],
    "差不多": ["相差無幾"],
    "知書識禮": ["知書達禮"],
    "聞名遐邇": ["馳名中外"],
    "長途跋涉": ["遠行"],
    "使用手冊": ["參考書"],
    "勇往直前": ["一往直前"],
}

PROPER = {
    "新華日報",
    "多米尼克",
    "嫦娥奔月",
    "文殊菩薩",
    "雲岡石窟",
    "上合組織",
    "水木清華",
    "克林黴素",
    "北戴河區",
    "四書五經",
    "三國時代",
    "拉米夫定",
    "蘇州地區",
    "三民主義",
    "越王勾踐",
    "達斡爾族",
    "阿布哈茲",
    "盤古開天",
    "大禹治水",
    "普賢菩薩",
    "五代十國",
    "人魚小姐",
    "寧波地區",
    "正鑲白旗",
    "儒林外史",
    "塔里木河",
    "良渚文化",
}

POLY = {
    "冷血動物",
    "有色眼鏡",
    "空中飛人",
}

CULTURAL = {
    "寧靜致遠",
    "殺人放火",
    "百年好合",
    "良辰美景",
    "顧全大局",
    "齊人之福",
    "刀槍不入",
    "千錘百鍊",
    "拜師學藝",
    "掛在嘴上",
    "改朝換代",
    "站不住腳",
    "貪小便宜",
    "逼上梁山",
    "人情冷暖",
    "放手一搏",
    "異國情調",
    "親自出馬",
    "身懷絕技",
    "大不如前",
    "懸而未決",
    "捨我其誰",
    "據理力爭",
    "於心不忍",
    "曲徑通幽",
    "群雄逐鹿",
    "重色輕友",
    "靜觀其變",
    "不惑之年",
    "假戲真做",
    "年輕貌美",
    "恍如隔世",
    "欲蓋彌彰",
    "深情款款",
    "白雪皚皚",
    "矇混過關",
    "結伴同行",
    "酒足飯飽",
    "三十而立",
    "乍暖還寒",
    "兩肋插刀",
    "少兒不宜",
    "引咎辭職",
    "收放自如",
    "機關算盡",
    "老夫老妻",
    "苦中作樂",
    "見好就收",
    "見過世面",
    "醉翁之意",
    "一笑了之",
    "不可挽回",
    "臨危受命",
    "調虎離山",
    "逃離現場",
    "連根拔起",
    "中庸之道",
    "乏善可陳",
    "反面教材",
    "叮叮噹噹",
    "嬉笑怒罵",
    "對簿公堂",
    "左擁右抱",
    "濛濛細雨",
    "白駒過隙",
    "百看不厭",
    "神來之筆",
    "素面朝天",
    "陽春白雪",
    "龍鳳呈祥",
    "一腔熱血",
    "不成比例",
    "凹凸有致",
    "展翅高飛",
    "正是如此",
    "治病救人",
    "登堂入室",
    "置身其中",
    "能歌善舞",
    "自取其辱",
    "請君入甕",
    "鮮血淋漓",
    "不惜犧牲",
    "同牀共枕",
    "君子之交",
    "喧賓奪主",
    "塞翁失馬",
    "情意綿綿",
    "打草驚蛇",
    "男才女貌",
    "看不過去",
    "老少皆宜",
    "要死要活",
    "不讓鬚眉",
    "春華秋實",
    "睡眼惺忪",
    "金髮碧眼",
    "魚與熊掌",
    "黃道吉日",
    "不可限量",
    "任人宰割",
    "可喜可賀",
    "大雅之堂",
    "尊老愛幼",
    "屢試不爽",
    "席地而坐",
    "河東獅吼",
    "浪子回頭",
    "百聽不厭",
    "空手而歸",
    "蓋世英雄",
    "鹹魚翻身",
    "披頭散髮",
    "活學活用",
    "男左女右",
    "眼淚汪汪",
    "秋水伊人",
    "負有責任",
    "載入史冊",
    "互不相讓",
    "刻苦鑽研",
    "夜不歸宿",
    "歷久彌新",
    "深受感動",
    "無牽無掛",
    "細嚼慢嚥",
    "連滾帶爬",
    "俗不可耐",
    "偷天換日",
    "孤魂野鬼",
    "情真意切",
    "春花秋月",
    "萬萬不可",
    "葬身之地",
    "造福人類",
    "遊戲人間",
    "來者不善",
    "出師不利",
    "卑鄙無恥",
    "危機重重",
    "才貌雙全",
    "欺人太甚",
    "氣勢如虹",
    "物極必反",
    "節節敗退",
    "自學成才",
    "雅俗共賞",
    "面目猙獰",
    "魑魅魍魎",
    "一潭死水",
    "以訛傳訛",
    "各有所長",
    "大雪紛飛",
    "奇花異草",
    "毫無價值",
    "肌肉發達",
    "裝神弄鬼",
    "開國元勳",
    "一葉扁舟",
    "傷亡慘重",
    "利國利民",
    "屢戰屢敗",
    "山崩地裂",
    "父母雙亡",
    "生財之道",
    "繁星點點",
    "長驅直入",
    "飛鴿傳書",
    "香消玉殞",
    "三妻四妾",
    "人面桃花",
    "冰雪聰明",
    "妙齡少女",
    "恩愛夫妻",
    "搶購一空",
    "禍國殃民",
    "胎死腹中",
    "自甘墮落",
    "良家婦女",
    "飛檐走壁",
    "大幹一場",
    "對酒當歌",
    "收拾殘局",
    "自彈自唱",
    "花容失色",
    "衣食父母",
    "話到嘴邊",
    "閒雲野鶴",
    "人海茫茫",
    "劍走偏鋒",
    "四季如春",
    "安安心心",
    "實屬不易",
    "有錢有勢",
    "求同存異",
    "生死未卜",
    "精忠報國",
    "蔚然成風",
    "分一杯羹",
    "心存僥倖",
    "日趨嚴重",
    "波瀾起伏",
    "知恩圖報",
    "笑臉相迎",
    "人無完人",
    "後繼有人",
    "權衡利弊",
    "聰明絕頂",
    "落地生根",
    "踏雪尋梅",
    "黑白兩道",
    "三頭六臂",
    "倒背如流",
}

OTHER = {
    "單核細胞",
    "機會主義",
    "聚酰亞胺",
    "肌肉注射",
    "行政單位",
    "運動神經",
    "分工合作",
    "商品生產",
    "民族工業",
    "照明設備",
    "開發週期",
    "名譽會長",
    "異常現象",
    "三房一廳",
    "分組討論",
    "叫醒服務",
    "婦科醫生",
    "收盤價格",
    "核糖核酸",
    "許可協議",
    "酒精中毒",
    "交換技術",
    "公費醫療",
    "演出地點",
    "纖維工業",
    "休閒活動",
    "平板玻璃",
    "拔河比賽",
    "有婦之夫",
    "社會形態",
    "社會意識",
    "第二課堂",
    "自來水管",
    "自由戀愛",
    "良種繁育",
    "傳輸設備",
    "商業發票",
    "教育局長",
    "包皮環切",
    "同父異母",
    "存在主義",
    "社會存在",
    "軍事學院",
    "地下錢莊",
    "產科醫生",
    "視頻節目",
    "三農問題",
    "出庭作證",
    "碎片整理",
    "雄性激素",
    "音頻設備",
    "應用物理",
    "文藝活動",
    "有關各方",
    "液壓傳動",
    "資訊科技",
    "黑白電視",
    "一般貿易",
    "危重病人",
    "基本單位",
    "太陽輻射",
    "專線電話",
    "拼圖遊戲",
    "燃氣輪機",
    "生產勞動",
    "自動恢復",
    "轟動效應",
    "麥田怪圈",
    "一式兩份",
    "分析處理",
    "守恆定律",
    "監管體制",
    "網絡語言",
    "臨牀特徵",
    "一夫多妻",
    "催化裂化",
    "潤腸通便",
    "生物材料",
    "行使職權",
    "財政年度",
    "開放政策",
    "充分就業",
    "共同基金",
    "化學變化",
    "收復失地",
    "海軍基地",
    "現代五項",
    "電機工程",
    "地震預報",
    "小麥胚芽",
    "市民社會",
    "有限元法",
    "約束條件",
    "能源危機",
    "自行決定",
    "雙重標準",
    "丹霞地貌",
    "反導系統",
    "國家機器",
    "天然纖維",
    "抗壞血酸",
    "理性認識",
    "聯合政府",
    "國事訪問",
    "持槍搶劫",
    "軍備競賽",
    "隔熱材料",
    "一般規定",
    "外生殖器",
    "氫氧化鋁",
    "皮下注射",
    "肌肉組織",
    "自由意志",
    "解放運動",
    "農業社會",
    "過渡金屬",
    "優化組合",
    "友好訪問",
    "工業時代",
    "授權範圍",
    "火災現場",
    "燃煤鍋爐",
    "自行解決",
    "造紙工業",
    "主權國家",
    "四捨五入",
    "強烈願望",
    "福利事業",
    "車牌號碼",
    "點火開關",
    "不當得利",
    "戰略轟炸",
    "物質享受",
    "義務勞動",
    "乒乓球拍",
    "催化作用",
    "天主教徒",
    "教育部長",
    "種子選手",
    "立體電影",
    "細胞色素",
    "緊密配合",
    "輸入設備",
    "輻射防護",
    "雄性不育",
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
        for ln in (FIXT / "syn_len4_b04_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
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

    (FIXT / "syn_len4_b04_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b04_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b04_adequate.tsv").write_text(
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
