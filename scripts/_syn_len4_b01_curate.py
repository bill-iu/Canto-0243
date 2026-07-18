"""Curate syn_len4 batch-1 fixtures (ranks 1–500)."""
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
BATCH = "syn-len4-b01-20260718"

# head -> preferred near-synonym tail (must resolve into lexicon via pick_tail)
RAW: dict[str, str] = {
    "唔經唔覺": "不知不覺",
    "異口同聲": "眾口一詞",
    "其他地方": "別處",
    "殺毒軟件": "防毒軟件",
    "電子郵件": "電郵",
    "環境保護": "環保",
    "手提電話": "手機",
    "豬朋狗友": "狐朋狗友",
    "不可避免": "在所難免",
    "事到如今": "事已至此",
    "智能手機": "智能電話",
    "驅動程序": "驅動程式",
    "不切實際": "脫離實際",
    "意大利粉": "意粉",
    "國際貿易": "外貿",
    "奧林匹克": "奧運",
    "高新技術": "高科技",
    "專業知識": "專門知識",
    "天氣預報": "天氣預測",
    "負面影響": "消極影響",
    "世界經濟": "國際經濟",
    "弱勢羣體": "弱勢社羣",
    "股票市場": "股市",
    "生活水平": "生活水準",
    "恐怖分子": "恐怖份子",
    "一廂情願": "一相情願",
    "城鎮居民": "城市居民",
    "無處不在": "無所不在",
    "質量管理": "品質管理",
    "求求其其": "馬馬虎虎",
    "源源不絕": "源源不斷",
    "滔滔不絕": "口若懸河",
    "流行音樂": "流行曲",
    "公共場所": "公眾場所",
    "生活環境": "居住環境",
    "下定決心": "下決心",
    "不良反應": "副作用",
    "隨處可見": "比比皆是",
    "參考文獻": "參考書目",
    "心理健康": "精神健康",
    "程序設計": "編程",
    "日光日白": "光天化日",
    "投資銀行": "投行",
    "各不相同": "各異",
    "快手快腳": "手急眼快",
    "公共交通": "大眾運輸",
    "郵政編碼": "郵遞區號",
    "政府機關": "政府機構",
    "網絡環境": "網路環境",
    "興致勃勃": "興高采烈",
    "中央銀行": "央行",
    "恐怖襲擊": "恐襲",
    "現場直播": "直播",
    "難以想象": "難以想像",
    "可見一斑": "略見一斑",
    "大吉利是": "大吉大利",
    "夾手夾腳": "礙手礙腳",
    "刑事責任": "刑責",
    "受益匪淺": "獲益良多",
    "高分辨率": "高清晰度",
    "全力支持": "鼎力支持",
    "外匯市場": "匯市",
    "基本建設": "基建",
    "撕心裂肺": "肝腸寸斷",
    "公共關係": "公關",
    "前提條件": "先決條件",
    "牀上用品": "寢具",
    "電子信箱": "電郵",
    "畢業典禮": "畢業禮",
    "對衝基金": "對沖基金",
    "貨物運輸": "貨運",
    "後期製作": "後製",
    "公用事業": "公共事業",
    "一家大細": "一家大小",
    "人仔細細": "小心翼翼",
    "出雙入對": "成雙成對",
    "房產中介": "房屋中介",
    "天壤之別": "天淵之別",
    "僅此而已": "如此而已",
    "唯物主義": "唯物論",
    "女主人公": "女主角",
    "夢中情人": "夢中人",
    "工作小組": "工作組",
    "養家餬口": "養家活口",
    "通俗易懂": "淺顯易懂",
    "數字信號": "數位信號",
    "民意調查": "民調",
    "延年益壽": "益壽延年",
    "傳輸速率": "傳輸率",
    "勤工儉學": "半工半讀",
    "字裏行間": "字裡行間",
    "不一會兒": "不一會",
}

ALTS: dict[str, list[str]] = {
    "脫離實際": ["脱離實際"],
    "弱勢社羣": ["弱勢社群"],
    "國際經濟": ["環球經濟"],
    "城市居民": ["城鎮居民"],
    "源源不斷": ["源源不絕"],
    "居住環境": ["生活環境"],
    "政府機構": ["政府機關"],
    "肝腸寸斷": ["痛不欲生"],
    "電郵": ["電子郵件"],
    "股市": ["股票市場"],
}

# proper names / brands / titles / orgs
PROPER = {
    "佛羅倫斯",
    "三國演義",
    "星際爭霸",
    "馬拉多納",
    "莎士比亞",
    "哈根達斯",
    "勞斯萊斯",
    "忍者神龜",
    "香港大學",
    "五角大樓",
    "諾貝爾獎",
    "國際足聯",
    "世界銀行",
    "青藏高原",
    "科技大學",
    "生化危機",
    "我愛我家",
    "四大天王",
    "十二生肖",
    "藝術學院",
    "教育學院",
    "中國大陸",
}

# opaque cultural / idiom with no stable binary near-syn
CULTURAL = {
    "男人老狗",
    "似曾相識",
    "話口未完",
    "一頭霧水",
    "講開又講",
    "九唔搭八",
    "見步行步",
    "睇唔過眼",
    "忍無可忍",
    "與時俱進",
    "山長水遠",
    "一廂情願",  # kept in RAW; if RAW wins, not used
    "不知所謂",
    "恭喜發財",
    "深入人心",
    "後顧之憂",
    "高高在上",
    "一片空白",
    "大打折扣",
    "善解人意",
    "紅顏知己",
    "一席之地",
    "日新月異",
    "耳目一新",
    "命中註定",
    "風花雪月",
    "撲面而來",
    "錦上添花",
    "字裏行間",  # in RAW
    "撕心裂肺",  # in RAW
    "不離不棄",
    "勢在必行",
    "橫空出世",
    "歷歷在目",
    "世界末日",
    "大可不必",
    "日復一日",
    "無私奉獻",
    "古今中外",
    "漫無目的",
    "曇花一現",
    "炙手可熱",
    "功不可沒",
    "天人合一",
    "雞皮疙瘩",
    "心有靈犀",
    "欲罷不能",
    "悲歡離合",
    "心有餘悸",
    "十有八九",
    "花樣年華",
    "黑色幽默",
    "可圈可點",
    "歡聲笑語",
    "紅杏出牆",
    "三位一體",
    "十面埋伏",
    "擦身而過",
    "詩情畫意",
    "走火入魔",
    "第一桶金",
    "蓄勢待發",
    "朝夕相處",
    "梅開二度",
    "半壁江山",
    "對症下藥",
    "就事論事",
    "拒之門外",
    "空無一人",
    "興致勃勃",  # in RAW
    "可見一斑",  # in RAW
    "相安無事",  # in RAW
    "受益匪淺",  # in RAW
    "天壤之別",  # in RAW
    "僅此而已",  # in RAW
    "延年益壽",  # in RAW
    "無怨無悔",  # in RAW
    "風情萬種",  # in RAW
    "通俗易懂",  # in RAW
    "出雙入對",  # in RAW
    "人仔細細",  # in RAW
    "大吉利是",  # in RAW
    "夾手夾腳",  # in RAW
    "日光日白",  # in RAW
    "快手快腳",  # in RAW
    "豬朋狗友",  # in RAW
    "求求其其",  # in RAW
    "唔經唔覺",  # in RAW
    "異口同聲",  # in RAW
    "源源不絕",  # in RAW
    "滔滔不絕",  # in RAW
    "無處不在",  # in RAW
    "隨處可見",  # in RAW
    "傷痕累累",  # in RAW
}

# legal / boilerplate / slogan / opaque technical compounds
OTHER = {
    "版權所有",
    "生日快樂",
    "新年快樂",
    "僅供參考",
    "免責聲明",
    "歡迎光臨",
    "注意安全",
    "忘記密碼",
    "貨到付款",
    "廠家直銷",
    "密碼保護",
    "發生關係",
    "改革開放",
    "全國人民",
    "國家安全",
    "國家標準",
    "帝國主義",
    "意識形態",
    "精神文明",
    "核心價值",
    "工人階級",
    "團隊精神",
    "敬業精神",
    "絕對優勢",
    "穿越時空",
    "法律效力",
    "開拓創新",
    "轉移支付",
    "社區建設",
    "知識經濟",
    "藍天白雲",
    "物質文明",
    "操作規程",
    "專題研究",
    "優秀學生",
    "週年紀念",
    "證券市場",
    "刑事拘留",
}

POLY: set[str] = {
    "怎麼回事",
    "一個二個",
    "有關方面",
    "各界人士",
    "認識自己",
    "飛來飛去",
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
        for ln in (FIXT / "syn_len4_b01_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
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
    (FIXT / "syn_len4_b01_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b01_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_len4_b01_adequate.tsv").write_text(
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
