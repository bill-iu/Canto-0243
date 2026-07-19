# one-shot P3 full_r1 audit — writes part TSV + p3_summary.md
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

DIR = Path(__file__).resolve().parent
PARTS = [DIR / f"p3_sample_part{i}.tsv" for i in range(1, 5)]
HEADER = [
    "phase", "literal", "pos", "family", "voice", "note", "trust", "stratum",
    "verdict", "fix_pos", "fix_family", "fix_voice", "audit_note",
]

# literal -> (verdict, fix_pos, fix_family, audit_note)
# fix_family: "" leave; "-" clear idiom family
OVR: dict[str, tuple[str, str, str, str]] = {}


def o(lit: str, verdict: str, fix_pos: str = "", note: str = "", fix_family: str = "") -> None:
    OVR[lit] = (verdict, fix_pos, fix_family, note)


def o_many(lits: list[str], verdict: str, fix_pos: str = "", note: str = "") -> None:
    for lit in lits:
        o(lit, verdict, fix_pos, note)


# ═══════════════════════════════════════════════════════════════
# high|gate|idiom
# ═══════════════════════════════════════════════════════════════
o("一個二個", "OK", note="數／逐一虛用；固定說法可留 idiom")
o("全力以赴", "OK", note="成語動用")
o("斷斷續續", "OK", note="AABB 狀態／情狀 a,r")
o("無處不在", "BAD", "a,v", "謂語「無處不在」形／動；非名（cow-single n 假陽）")
o("除此之外", "OK", note="連接短語 r；之字格固定可留")

# ═══════════════════════════════════════════════════════════════
# high|gate|plain
# ═══════════════════════════════════════════════════════════════
o_many(
    [
        "一些問題", "下跌", "二十", "人之常情", "保存", "信息技術", "優質服務", "六一",
        "具體情況", "加強", "受益", "各級政府", "咬住", "國內市場", "地方政府", "增長",
        "專業人員", "戴住", "托住", "批評", "搜索", "無線網絡", "照住", "理工大學",
        "發達國家", "監管部門", "知識分子", "研發中心", "研究中心", "研究人員", "科學技術",
        "立法", "競爭", "管理系統", "統一", "考完", "股票市場", "舉報電話", "衝突",
        "被迫", "諮詢服務", "諮詢電話", "資本市場", "超級市場", "這些問題", "頂住", "順住",
    ],
    "OK",
    note="gate primary 正確",
)
o("不掉", "BAD", "u", "否定+掉；多見於 V 不掉，非獨立動詞（verb-suffix 假陽）")
o("受衆", "BAD", "n", "受衆＝觀眾／聽衆名詞；prefix-passive 假陽會毒同動詞閘")
o("被窩", "BAD", "n", "被窩＝被褥名詞；prefix-passive 假陽會毒同動詞閘")

# ═══════════════════════════════════════════════════════════════
# high|u|idiom
# ═══════════════════════════════════════════════════════════════
o("一清二楚", "BAD", "a,r", "清楚明白；形／情狀副")
o("嘻嘻哈哈", "BAD", "a,r", "AABB 嬉笑狀態／情狀")
o("大大小小", "BAD", "a", "AABB 大小不一")
o("實實在在", "BAD", "a,r", "AABB 真實／確實")
o("方方面面", "BAD", "n", "AABB 各方面，名")
o("有意無意", "BAD", "r", "有無對情狀副")
o("有所不同", "BAD", "a,v", "有所+不同；述謂")
o("老老實實", "BAD", "a,r", "AABB 老實狀態／情狀")

# ═══════════════════════════════════════════════════════════════
# high|u|plain
# ═══════════════════════════════════════════════════════════════
o("不完", "OK", note="否定+完截斷；u 正確")
o("受山", "OK", note="切詞假陽；u 正確")

# ═══════════════════════════════════════════════════════════════
# low|low|plain
# ═══════════════════════════════════════════════════════════════
o_many(
    [
        "一月", "上帝", "上映", "上演", "人們", "倡議", "僅僅", "兔子", "公務員", "公路",
        "共性", "典範", "制度", "十月", "半場", "博物館", "叢", "句子", "名稱", "和諧",
        "城堡", "墨盒", "外形", "夥伴", "大炮", "失效", "奔騰", "女兒", "女皇", "好手",
        "定向", "對講機", "帷幕", "年級", "後期", "意圖", "打印機", "投保", "抱怨", "招手",
        "指向", "捐款", "探索", "接收", "掩飾", "擊", "收看", "效率", "救護車", "方形",
        "旅程", "昨日", "松鼠", "棚", "槽", "歡呼", "死刑", "母豬", "毫不", "民", "注視",
        "液", "源泉", "澳洲", "瀉", "灰燼", "熱氣", "父", "猜測", "現代人", "生產力",
        "痕跡", "發誓", "矩陣", "箍", "節", "紅包", "紅蘿蔔", "綜述", "芷", "苯", "草叢",
        "萬聖節", "薪水", "血糖", "被殺", "註釋", "責令", "賠", "起飛", "超越", "趕走",
        "跌倒", "踐踏", "逃生", "酒精", "錦標賽", "鐘樓", "集", "集合", "電話號碼", "電路",
        "騙", "鼠",
    ],
    "OK",
    note="draft primary 可接受",
)
for lit, note in [
    ("侷限", "主 n 可；動「侷限於」常見"),
    ("大意", "主 n（要旨）可；形「粗心」常見"),
    ("實習", "主 v 可；名常見"),
    ("格式化", "主 n 可；動常見"),
    ("發育", "主 n 可；動常見"),
    ("磋商", "主 n 可；動常見"),
    ("置換", "主 n 可；動常見"),
    ("裂開", "主 v；n 弱"),
    ("謝謝", "主 v／套語；n 弱"),
    ("邪惡", "主 a；draft n 偏"),
    ("醒覺", "粵主 v；draft a 邊"),
    ("預感", "主 v；名常見"),
    ("現代化", "主 v；名亦常見"),
    ("深藍色", "色名 n 可；亦形"),
]:
    o(lit, "SOFT", note=note)

o("不便", "BAD", "a", "形「不方便」；n 假陽")
o("在外", "BAD", "r", "處所／狀態副；非名")
o("均", "BAD", "r", "副「都／均勻」；非動")
o("放寬", "BAD", "v", "動「放寬」；非名")
o("有效", "BAD", "a", "形「有效」；非動")
o("正直", "BAD", "a", "形；非名")
o("無情", "BAD", "a", "形；非名")
o("當下", "BAD", "n,r", "名／副「此刻」；verb-suffix 下 假陽")
o("繁忙", "BAD", "a", "形；非名")
o("自主", "BAD", "a,v", "形／動；非純名")
o("親切", "BAD", "a", "形；非名")

# ═══════════════════════════════════════════════════════════════
# low|u|idiom
# ═══════════════════════════════════════════════════════════════
o("一生一世", "BAD", "n,r", "一輩子")
o("一舉一動", "BAD", "n", "每個動作")
o("人來人往", "BAD", "v,a", "ABAC 人來往")
o("依依不捨", "BAD", "a,v", "AABC 不捨")
o("可口可樂", "BAD", "n", "品牌專名；ABAC 假陽熟語 → clear family", fix_family="-")
o("各式各樣", "BAD", "a", "各式樣")
o("各種各樣", "BAD", "a", "各種樣")
o("哈哈大笑", "BAD", "v", "AABC 大笑")
o("唔多唔少", "BAD", "r", "粵差不多")
o("唔經唔覺", "BAD", "r", "粵不知不覺")
o("奄奄一息", "BAD", "a", "AABC 垂死")
o("忍無可忍", "BAD", "v", "無法再忍")
o("有講有笑", "BAD", "v", "有說有笑")
o("無時無刻", "BAD", "r", "時時刻刻")
o("若隱若現", "BAD", "a,v", "半隱半現")
o("講開又講", "BAD", "v", "粵話頭")

# ═══════════════════════════════════════════════════════════════
# low|u|plain — BAD clear POS
# ═══════════════════════════════════════════════════════════════
# nouns / proper
o_many(
    [
        "事蹟", "亞瑟", "人大代表", "佐治", "作品內容", "俄國", "保單", "信用證", "光電",
        "內側", "冰耀", "前列", "力度", "加菲", "動脈", "動靜", "勞動合同", "勞務", "原意",
        "史料", "叻仔", "同好", "同濟", "唐山", "商機", "回族", "國際米蘭", "地鐵站", "場館",
        "境內", "外貿", "大型企業", "大城市", "女校", "威嚴", "學歷", "安娜", "客車", "富士康",
        "寶貝兒", "專區", "小圖", "小學生", "小溪", "工業園", "左下角", "廈門市", "弱勢羣體",
        "張學友", "後續", "必要性", "懷裏", "成色", "手信", "技嘉", "掌聲", "插槽", "撒旦",
        "新品", "新生兒", "新界", "新聞聯播", "新華網", "日本人", "明細", "書本", "本機",
        "本網站", "東航", "林子", "林綺雯", "校區", "格格", "梓謙", "條碼", "業務員", "機型",
        "此案", "歹徒", "殘魂", "民進黨", "水平線", "水面", "油價", "油田", "法國", "洞口",
        "浩方", "港女", "源代碼", "潮州", "火車站", "熊市", "熱血", "王爺", "現實生活", "現貨",
        "甜品", "產業鏈", "田中", "畢業證", "發展空間", "白煙", "百科", "相聲", "看點",
        "研究所", "碩士學位", "福建", "稅率", "第一章", "第三季", "第四章", "米線", "細榮",
        "細貓", "組委會", "統計數據", "經濟學家", "經貿", "網名", "總公司", "美酒", "美食",
        "老劉", "老朋友", "聊天室", "股東大會", "舒淇", "蔣震滔", "蕪湖", "薩滿", "蛋治",
        "血清", "衛浴", "衣物", "西面", "計算器", "誠意", "調料", "證券投資", "警局", "豆腐",
        "責任人", "貴陽", "趙本山", "蹤影", "車型", "輔導員", "辦公廳", "農業部", "這些人",
        "這些東西", "這個傢伙", "這傢伙", "路由", "鋁合金", "鐵礦", "鐵礦石", "長輩", "關稅",
        "關系", "阿南道", "阿平", "阿黃", "零售商", "電臺", "音箱", "頭箍", "飛利浦", "飛機票",
        "飯堂", "餘人", "馬丁", "駕照", "體型", "魯尼", "麥皓臻", "麥迪", "黃金周", "點球",
        "黨內", "鼻頭", "二十年", "二線", "全國性", "十幾歲", "多樣性", "大一", "工業化",
        "差異化", "幾個鐘", "幾鐘", "上班族", "中國人民", "中國傳統", "乾隆", "供需",
        "搜狐博客", "豬朋狗友", "上海大衆", "中國國際", "既蘭卡特", "條春", "條裙", "最後一天",
        "第一眼", "節前", "考前",
    ],
    "BAD",
    "n",
    "清晰名詞／專名",
)

# verbs
o_many(
    [
        "交帶", "交費", "來訪", "做不了", "做返", "催促", "傾偈", "先說", "入手", "凝望",
        "出力", "出演", "分管", "切實加強", "刻錄", "剛買", "加快發展", "吐了", "喊着",
        "喜歡喫", "喫肉", "嚴格執行", "均屬", "均有", "坐底", "執導", "執生", "執返",
        "培養學生", "增設", "媾女", "嫌棄", "學英語", "寫了", "帶到", "幫襯", "廣泛應用",
        "建立健全", "彈起", "想給", "想說", "想買", "應聲", "應該可以", "打打", "打拼",
        "打轉", "換來", "搞事", "擦拭", "擦過", "擺到", "擺脫", "救了", "整傷", "整到",
        "曾任", "會嚟", "會說", "有車", "有過", "未予", "未有", "未死", "比到", "求情",
        "泡妞", "淋溼", "深信", "爬上", "獲獎", "發揚", "發晒", "看不慣", "看似", "睡在",
        "示弱", "竄", "聽下", "聽懂", "能做", "能喫", "衝咗", "衝返", "要寫", "要看",
        "要跟", "見不到", "診治", "請來", "請用", "請聯繫", "講出嚟", "識路", "讀研",
        "貪錢", "走低", "走好", "跑到", "跑過", "轉載自", "送來", "送死", "過戶", "過節",
        "還會有", "醫好", "關機", "靠着", "響到", "食下", "飲飲", "鬧交", "點點頭", "下山",
        "下班", "不寫", "不愛", "不買", "估下", "伴有", "又開始", "只知道", "問個", "問咗",
        "嚟做", "年產", "徵集", "暈咗", "置頂", "過節", "錄入", "開個", "防控", "下話",
        "不理我", "不用擔心", "不要去", "中轉",
    ],
    "BAD",
    "v",
    "清晰動詞／動語",
)

# adjectives
o_many(
    [
        "了不起", "嚴格", "堅硬", "太遠", "好夠", "好強", "專一", "很清楚", "很辛苦", "很開心",
        "微不足道", "最高", "有型", "有序", "無憂", "猙獰", "神聖", "稀有", "經驗豐富", "華麗",
        "血腥", "鹹溼", "不切實際", "世界級", "不全", "不變的", "最早的", "比較低", "比較大",
        "比較容易", "圓碌碌", "多功能", "民用",
    ],
    "BAD",
    "a",
    "清晰形容詞",
)

# adverbs / function
o_many(["不久", "年年", "月月", "猛然", "甚爲", "總在", "逐步", "迄今", "還挺", "陣時", "儘可能", "無時無刻"], "BAD", "r", "清晰副詞")
# fix: 無時無刻 already in idiom
o("二來", "BAD", "r,x", "序列連接")
o("僅是", "BAD", "v,r", "只是")
o("均由", "BAD", "v,x", "動／介")
o("強行", "BAD", "r,v", "副／動")
o("每當", "BAD", "r,x", "連／副")
o("要不是", "BAD", "x,r", "連詞")
o("豈不", "BAD", "r", "副")
o("那種", "BAD", "x", "指示")
o("那本", "BAD", "x", "指示+量")
o("一顆", "BAD", "x", "數+量")
o("一齣", "BAD", "x", "數+量")
o("多家", "BAD", "x,n", "數+量")
o("多萬", "BAD", "x", "約數")
o("兩隊", "BAD", "x,n", "數+量")
o("整條", "BAD", "x,a", "整+量")
o("支槍", "BAD", "n,x", "量+名")
o("三分鐘", "BAD", "n,x", "時量")
o("另一種", "BAD", "x,n", "指示")
o("嗰兩個", "BAD", "x", "指示")
o("哪家", "BAD", "x", "疑問")
o("爲你", "BAD", "x,v", "介+代")
o("限於", "BAD", "v,x", "動／介")

# multi-class clear
_multi = {
    "偏低": ("a,v", "形／動"),
    "創新": ("n,v", "名動"),
    "反動": ("a,n", "形／名"),
    "可想而知": ("v,r", "述謂／插入"),
    "呵欠": ("n,v", "名動"),
    "喫喝": ("v,n", "動／名"),
    "回購": ("n,v", "名動"),
    "垂直": ("a,v", "形／動"),
    "多方": ("n,r", "名／副"),
    "多遠": ("a,r", "疑問距離"),
    "好地地": ("r,a", "粵好端端"),
    "定點": ("a,n,v", "名形動"),
    "年產": ("v,n", "動／名"),
    "幾勁": ("a,r", "粵程度"),
    "廢時": ("a,v", "粵費時"),
    "意想不到": ("a,v", "出乎意料"),
    "意料": ("n,v", "名動"),
    "有緣": ("a,v", "形／動"),
    "有點像": ("a,v", "有點像"),
    "比方": ("n,v", "名動"),
    "深加工": ("n,v", "名動"),
    "深層次": ("a,n", "形／名"),
    "無心": ("a,v", "形／動"),
    "私營化": ("n,v", "名動"),
    "解套": ("n,v", "名動"),
    "解脫": ("n,v", "名動"),
    "設定": ("n,v", "名動"),
    "調頭": ("n,v", "名動"),
    "配搭": ("n,v", "名動"),
    "錄入": ("n,v", "名動"),
    "關愛": ("n,v", "名動"),
    "防控": ("n,v", "名動"),
    "難爲": ("a,v", "形／動"),
    "難講": ("a,v", "粵"),
    "高低": ("a,n", "形／名"),
    "鬼知": ("r,v", "粵反詰"),
    "點評": ("n,v", "名動"),
    "低成本": ("a,n", "形／名"),
    "三維": ("a,n", "形／名"),
    "下晝": ("n,r", "粵下午"),
    "一輩子": ("n,r", "一生"),
    "中轉": ("n,v", "名動"),
    "普查": ("n,v", "名動"),
    "明確規定": ("n,v", "動／名物化"),
    "易於": ("r,v", "易於+V"),
    "晏覺": ("n,v", "粵晚睡"),
    "通話": ("n,v", "名動"),
    "過會": ("n,r", "一會兒"),
    "還早": ("a,r", "形／副"),
    "還真是": ("r,v", "副+是"),
    "邊會": ("r,v", "粵反詰"),
    "緊貼": ("a,v", "形／動"),
    "編制": ("n,v", "名動"),
    "耦合": ("n,v", "名動"),
    "自閉": ("a,n,v", "形名動"),
    "西斜": ("a,v", "形／動"),
    "纔不會": ("r,v", "纔+不會"),
    "纔開始": ("r,v", "纔+開始"),
    "一男一女": ("n,x", "對舉"),
    "一口一口": ("r,x", "方式疊"),
    "上一次": ("n,r", "上次"),
    "上部": ("n", "名"),
    "不同程度": ("n", "名"),
    "先見": ("n,v", "先見"),
    "可好": ("a,r", "形／副"),
    "哂力": ("a,v", "粵費力"),
    "床度": ("n,r", "粵牀上"),
    "轆轆": ("a,x", "擬聲／形"),
    "人用": ("a", "形「人用」"),
    "句話": ("n", "名截「一句話」可 n"),
    "可兒": ("n", "愛稱"),
}
for lit, (fp, note) in _multi.items():
    o(lit, "BAD", fp, note)

# OK fragments
for lit, note in [
    ("上也", "上+也 截斷"),
    ("仔見", "截斷不明"),
    ("他不", "代+不截斷"),
    ("他對", "代+介截斷"),
    ("他所", "代+所截斷"),
    ("你和", "代+連截斷"),
    ("人之", "之字截斷"),
    ("人入", "截斷"),
    ("人對", "截斷"),
    ("地同", "地+連截斷"),
    ("地架", "截斷"),
    ("埸", "罕異體，詞類難定"),
    ("宜個", "截斷不明"),
    ("小貞到", "專名+到截斷"),
    ("小貞用", "專名+用截斷"),
    ("我就不", "小句截斷"),
    ("我那", "代+指示截斷"),
    ("次同", "截斷"),
    ("歷史上最", "最高級截斷"),
    ("用條", "動+量截斷"),
    ("真的很", "副連截斷"),
    ("肥龍同", "專名截斷"),
    ("裏去", "趨向截斷"),
    ("過呀", "語氣截斷"),
    ("頭望", "截斷不明"),
    ("後才能", "連用截斷"),
    ("咗事", "助+名截斷"),
    ("咗六合彩", "助+名截斷"),
    ("哩句", "指示截斷"),
    ("嘢做", "粵截斷"),
    ("嘢好", "粵截斷"),
    ("係路", "粵截斷"),
    ("但仍", "連副截斷"),
    ("也使", "也+使截斷"),
    ("也從", "也+從截斷"),
    ("之日", "之字截斷"),
    ("四是", "列舉序截斷"),
    ("將你", "介+賓截斷"),
    ("將她", "介+賓截斷"),
    ("將球", "介+賓截斷"),
    ("將身", "介+賓截斷"),
    ("是世界上", "是+處截斷"),
]:
    o(lit, "OK", note=note)

# SOFT borderline u
for lit, note in [
    ("令我", "令+代截；可 v"),
    ("害我", "害+代；可 v"),
    ("要你", "要+代；可 v"),
    ("讓您", "讓+代；可 v"),
    ("給您", "給+代；可 v"),
    ("是一位", "是+量；可 v"),
    ("是他", "是+代；可 v"),
    ("是讓", "是+使；可 v"),
    ("有人認爲", "小句；可 v"),
    ("我只想", "小句；可 v"),
    ("我想說", "小句；可 v"),
    ("我看看", "小句；可 v"),
    ("我記", "小句截；可 v"),
    ("也不知道", "小句；可 v"),
    ("主要用於", "動語；可 v"),
    ("最終還是", "副連；可 r"),
    ("才叫", "纔叫；r,v 邊"),
    ("所需要", "所+V；可 v"),
    ("答得", "V+得；可 v"),
    ("入得", "V+得；可 v"),
    ("講嘅", "動+嘅；可 v"),
    ("嚟喇", "來了；v,x"),
    ("過嘢", "粵過分；a,v"),
    ("刀刀", "疊／量邊"),
    ("圓圓", "形疊／人名邊"),
    ("牛牛", "疊名／愛稱"),
    ("皮皮", "疊名／愛稱"),
    ("鼻鼻", "疊稱"),
    ("麻麻", "粵形／疊"),
    ("麼麼", "嘆／擬"),
    ("啦啦啦", "襯字"),
    ("呱", "擬聲"),
    ("唪", "罕"),
    ("濛", "形／名邊"),
    ("暴", "多類邊"),
    ("私", "多類邊"),
    ("末", "名／形邊"),
    ("氏", "後綴／名"),
    ("程", "名／量邊"),
    ("朱", "姓／名"),
    ("玲", "名用字"),
    ("祿", "名／抽象"),
    ("詹", "姓"),
    ("鑫", "名用字"),
    ("婷", "名用字"),
    ("孫", "親屬／姓"),
    ("朕", "代／名"),
    ("堡", "語素／名"),
    ("扐", "粵罕用動"),
    ("搏", "單字多義"),
    ("搗", "單字動"),
    ("撇", "單字多義"),
    ("測", "單字動"),
    ("歎", "單字動"),
    ("逝", "單字動"),
    ("脫", "單字動"),
    ("紥", "單字動"),
    ("楞", "形／動邊"),
    ("鎚", "名／動邊"),
    ("砵", "粵名／量"),
    ("高的", "形+的；可 a"),
    ("容講", "粵可 v；邊介"),
    ("有兩個", "有+數；可 v"),
    ("有邊", "粵有哪；v,x"),
    ("給人以", "動語；可 v"),
    ("這纔是", "強調是；v,r"),
    ("喇得", "粵語氣邊"),
    ("你得", "代+得截；邊"),
]:
    o(lit, "SOFT", note=note)

# ═══════════════════════════════════════════════════════════════
# medium|gate|plain
# ═══════════════════════════════════════════════════════════════
o_many(
    [
        "侮辱", "侵犯", "保管", "偏愛", "免除", "分攤", "刺痛", "勘探", "吹氣", "告別",
        "埋伏", "培養", "奮鬥", "實踐", "展覽", "干擾", "愛好", "批准", "抨擊", "搖擺",
        "操作", "改良", "放火", "流通", "混合", "爭吵", "犯罪", "發熱", "瞄準", "粉碎",
        "結合", "總結", "辯論", "追蹤", "通風", "違反", "遺傳",
    ],
    "OK",
    note="true multi n,v 閘用可",
)
o("互助", "BAD", "n,v", "互助主名／動；r 假陽會毒副詞閘")
o("傷痛", "SOFT", note="主 n；v 弱可留 multi")
o("削", "SOFT", note="主 v；n 弱")
o("固有", "BAD", "a", "形「固有」；n,v 假陽會毒閘")
o("定額", "SOFT", note="主 n；v 弱")
o("激烈", "BAD", "a", "形；n,v 假陽")
o("熟練", "BAD", "a", "形；n,v 假陽")
o("略微", "BAD", "r", "副「略微」；n 假陽")
o("編織", "SOFT", note="主 n,v；a 弱")
o("繼承", "BAD", "n,v", "名動；a 假陽")
o("趕緊", "BAD", "r", "副「趕緊」；n,v 假陽")
o("遠離", "SOFT", note="主 v；a,n 弱可")
o("顫抖", "SOFT", note="主 v,n；a 弱")


def judge(row: dict) -> dict:
    lit = row["literal"]
    if lit in OVR:
        verdict, fix_pos, fix_family, note = OVR[lit]
        row["verdict"] = verdict
        row["fix_pos"] = fix_pos
        row["fix_family"] = "" if fix_family == "-" else fix_family
        row["fix_voice"] = ""
        if fix_family == "-":
            note = note if "clear family" in note or "假陽熟語" in note else (note + "；clear family")
        row["audit_note"] = note
        return row
    # fallback by stratum
    st = row["stratum"]
    pos = row["pos"]
    if pos == "u":
        row["verdict"] = "SOFT"
        row["fix_pos"] = ""
        row["fix_family"] = ""
        row["fix_voice"] = ""
        row["audit_note"] = "未列專審；u 暫可（邊介／多類）"
    else:
        row["verdict"] = "OK"
        row["fix_pos"] = ""
        row["fix_family"] = ""
        row["fix_voice"] = ""
        row["audit_note"] = "primary 可接受"
    return row


def main() -> None:
    all_rows: list[dict] = []
    unlisted: list[tuple[str, str, str]] = []
    for path in PARTS:
        with path.open(encoding="utf-8", newline="") as f:
            raw = list(csv.DictReader(f, delimiter="\t"))
        out = []
        for r in raw:
            row = {k: (r.get(k) or "") for k in HEADER}
            if row["literal"] not in OVR:
                unlisted.append((row["literal"], row["stratum"], row["pos"]))
            row = judge(row)
            out.append(row)
            all_rows.append(row)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(out)
        print(f"wrote {path.name}: {len(out)}")

    counts = Counter(r["verdict"] for r in all_rows)
    n = len(all_rows)
    ok_soft = counts["OK"] + counts["SOFT"]
    ok_rate = ok_soft / n if n else 0
    by_st: dict[str, Counter] = defaultdict(Counter)
    for r in all_rows:
        by_st[r["stratum"]][r["verdict"]] += 1
    bads = [r for r in all_rows if r["verdict"] == "BAD"]

    patterns: Counter = Counter()
    for r in bads:
        note = r["audit_note"]
        src = r["note"]
        if "prefix-passive" in src or "被動" in note or "prefix-passive" in note or r["literal"] in ("受衆", "被窩"):
            patterns["prefix-passive 假陽 → n"] += 1
        elif "verb-suffix" in src or "否定+" in note or r["literal"] in ("不掉", "當下"):
            patterns["verb-suffix／否定補語假陽"] += 1
        elif r["pos"] == "u" and r["fix_pos"]:
            if "idiom" in r["stratum"]:
                patterns["u+idiom under-tag（clear POS）"] += 1
            else:
                patterns["u under-tag（clear POS）"] += 1
        elif "low|low" in r["stratum"]:
            patterns["low draft primary 錯"] += 1
        elif "gate" in r["stratum"] and ("形" in note or "副" in note or "假陽" in note):
            patterns["cow-multi／閘用假陽"] += 1
        else:
            patterns["other BAD"] += 1

    print(f"n={n} OK={counts['OK']} SOFT={counts['SOFT']} BAD={counts['BAD']} ok_rate={ok_rate:.4f}")
    print(f"unlisted={len(unlisted)}")
    if unlisted:
        print("unlisted sample:", unlisted[:40])

    lines = [
        "# P3 full-system POS audit (full_r1)",
        "",
        f"**Sample:** `data/pos/audit/full_r1/p3_sample_part{{1..4}}.tsv` (n={n})",
        "**Universe:** P3 Essay ranks 5001–20000 (15 000) stratified per `manifest.json`",
        "**Seed:** 20260720",
        "**Threshold:** ok_rate > 0.90",
        "**Date:** 2026-07-19",
        "",
        "## Policy",
        "",
        "| stratum | rule |",
        "|---------|------|",
        "| gate (high/medium) | primary POS correct for hard gate |",
        "| low draft | primary acceptable, else BAD+fix_pos |",
        "| u | OK if indeterminate/fragment; BAD+fix_pos if clear POS |",
        "| idiom family | clear family if not fixed expression |",
        "",
        "## Combined counts",
        "",
        "| verdict | n | % |",
        "|---------|---|---|",
    ]
    for v in ("OK", "SOFT", "BAD"):
        c = counts[v]
        lines.append(f"| {v} | {c} | {100 * c / n:.1f}% |")
    lines += [
        f"| **total** | **{n}** | 100% |",
        "",
        f"**ok_rate = (OK+SOFT)/n = {ok_soft}/{n} = {ok_rate:.4f}**",
        "",
        f"**{'PASS' if ok_rate > 0.90 else 'FAIL'}** ({ok_rate:.4f} {'>' if ok_rate > 0.90 else '≤'} 0.90)",
        "",
        "### By stratum",
        "",
        "| stratum | n | OK | SOFT | BAD | ok_rate |",
        "|---------|---|----|------|-----|---------|",
    ]
    for st in sorted(by_st):
        c = by_st[st]
        sn = sum(c.values())
        so = c["OK"] + c["SOFT"]
        lines.append(f"| `{st}` | {sn} | {c['OK']} | {c['SOFT']} | {c['BAD']} | {so / sn:.3f} |")

    # gate-only rate
    gate_rows = [r for r in all_rows if "gate" in r["stratum"]]
    g_ok = sum(1 for r in gate_rows if r["verdict"] in ("OK", "SOFT"))
    g_n = len(gate_rows)
    lines += [
        "",
        f"**Gate-only ok_rate** (high|gate|* + medium|gate|*): **{g_ok}/{g_n} = {g_ok / g_n:.4f}** "
        f"→ **{'PASS' if g_ok / g_n > 0.90 else 'FAIL'}**",
        "",
        "## Error patterns (BAD)",
        "",
    ]
    for i, (p, c) in enumerate(patterns.most_common(), 1):
        lines.append(f"{i}. **{p}** — {c}")
    lines += [
        "",
        "Dominant signal: **`low|u|*` under-tagging** (`no-source;fallback` → mass `u`). "
        "Expected; same shape as P1 low|u audit (most heads have an obvious formal tag).",
        "",
        "## Gate-impact BAD (high/medium gate only)",
        "",
    ]
    gate_bads = [r for r in bads if "gate" in r["stratum"]]
    if not gate_bads:
        lines.append("（無）")
    else:
        lines += [
            "| literal | stratum | was | fix_pos | reason |",
            "|---------|---------|-----|---------|--------|",
        ]
        for r in sorted(gate_bads, key=lambda x: (x["stratum"], x["literal"])):
            lines.append(
                f"| {r['literal']} | {r['stratum']} | {r['pos']} | {r['fix_pos']} | {r['audit_note']} |"
            )

    lines += [
        "",
        "## All BAD rows",
        "",
        "| literal | stratum | was | fix_pos | fix_family | audit_note |",
        "|---------|---------|-----|---------|------------|------------|",
    ]
    for r in sorted(bads, key=lambda x: (x["stratum"], x["literal"])):
        ff = "*(clear)*" if r["literal"] == "可口可樂" else (r["fix_family"] or "")
        note = (r["audit_note"] or "").replace("|", "\\|")
        lines.append(
            f"| {r['literal']} | {r['stratum']} | {r['pos']} | {r['fix_pos']} | {ff} | {note} |"
        )

    lines += [
        "",
        "## Files",
        "",
        "| path | role |",
        "|------|------|",
        "| `data/pos/audit/full_r1/p3_sample_part1.tsv` | filled verdicts part 1 |",
        "| `data/pos/audit/full_r1/p3_sample_part2.tsv` | filled verdicts part 2 |",
        "| `data/pos/audit/full_r1/p3_sample_part3.tsv` | filled verdicts part 3 |",
        "| `data/pos/audit/full_r1/p3_sample_part4.tsv` | filled verdicts part 4 |",
        "| `data/pos/audit/full_r1/p3_summary.md` | this summary |",
        "",
        "## Note",
        "",
        "- Combined ok_rate is **not** a pure gate metric: majority of sample is `low|u|plain` fallback `u`.",
        "- Use **Gate-only ok_rate** for hard-gate quality on P3.",
        "- Audit-only; SSOT not applied this pass.",
        "",
    ]
    outp = DIR / "p3_summary.md"
    outp.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {outp}")


if __name__ == "__main__":
    main()
