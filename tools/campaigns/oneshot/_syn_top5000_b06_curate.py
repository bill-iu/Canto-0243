"""Curate syn_top5000 batch-6 fixtures (final 148 heads)."""
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
BATCH = "syn-top5000-b06-20260718"

RAW = {
    "死心": "絕望",
    "流眼淚": "流淚",
    "用嚟": "用來",
    "發洩": "宣洩",
    "貴族": "皇族",
    "邊位": "邊個",
    "金色": "金黃色",
    "阿仔": "兒子",
    "鬧交": "吵架",
    "看上去": "看來",
    "存檔": "保存",
    "庫存": "存貨",
    "單手": "一手",
    "嗌交": "吵架",
    "四肢": "手脚",
    "壺": "水壺",
    "大大力": "用力",
    "好眼": "眼利",
    "客服": "服務員",
    "小息": "休息",
    "小隊": "小組",
    "沙律": "沙拉",
    "瘀": "瘀傷",
    "紋身": "刺青",
    "肉酸": "丟臉",
    "轉校": "轉學",
    "離家出走": "出走",
    "單元": "單位",
    "兩粒": "兩個",
    "反轉": "顛倒",
    "坐監": "坐牢",
    "姣": "騷",
    "宗教": "信仰",
    "慳": "節省",
    "我架": "我嘅",
    "整到": "搞到",
    "正所謂": "所謂",
    "牠": "它",
    "睇穿": "看穿",
    "緣份": "緣分",
    "開會": "會議",
    "頸鍊": "項鍊",
    "魚蛋": "魚丸",
    "是以": "因此",
    "國內外": "海內外",
    "一腳踢": "全能",
    "傻豬": "傻瓜",
    "冇心": "無心",
    "勢力": "權勢",
    "士多": "商店",
    "好勁": "厲害",
    "娘親": "母親",
    "市民": "居民",
    "探員": "偵探",
    "步行": "走路",
    "眼白白": "乾瞪眼",
    "等如": "等於",
    "背住": "背着",
    "蔔": "蘿蔔",
    "製": "製造",
    "輔導": "指導",
    "追上": "趕上",
    "雞翼": "翅膀",
    "測量": "量度",
    "斑竹": "版主",
    "得很": "非常",
    "乸": "雌",
    "合埋": "合攏",
    "咁滯": "幾乎",
    "好地地": "好好地",
    "孭": "揹",
    "小食": "零食",
    "愈嚟愈": "越來越",
    "日出": "黎明",
    "日落": "黃昏",
    "澈": "清澈",
    "甜筒": "雪糕",
    "結他": "吉他",
    "翻到": "翻去",
    "識講": "識講嘢",
    "豬扒": "豬排",
    "跪低": "跪下",
    "銀仔": "硬幣",
    "高中": "中學",
    "共有": "共同",
    "輸入法": "打字法",
    "七七八八": "差不多",
    "人仔": "人民幣",
    "初頭": "起初",
    "勤力": "勤奮",
    "喃喃": "嘀咕",
    "嗰度": "那裏",
    "奸笑": "壞笑",
    "急不及待": "迫不及待",
    "手指公": "拇指",
    "極之": "極其",
    "泳": "游泳",
    "狗公": "公犬",
    "瞇": "眯",
    "花名": "綽號",
    "落力": "盡力",
    "薯仔": "馬鈴薯",
    "變做": "變成",
    "邊間": "邊度",
    "開燈": "亮燈",
    "風水": "堪輿",
    "髮型": "頭型",
    "炒作": "哄抬",
    "最愛": "至愛",
    "研究所": "研究院",
    "做得": "可以",
    "其他人": "別人",
    "一嚟": "一來",
    "侍應": "侍應生",
    "勾起": "引起",
    "反問": "反詰",
    "唔覺意": "無意中",
    "好靜": "安靜",
    "嫌棄": "厭惡",
    "晨早": "早上",
    "有型": "時髦",
    "水族館": "海洋館",
    "泥膠": "黏土",
    "生還": "倖存",
    "的而且確": "的確",
    "茶餐廳": "茶室",
    "薯片": "脆片",
}

ALTS = {
    "絕望": ["灰心", "放棄"],
    "流淚": ["落淚", "哭"],
    "用來": ["用以"],
    "宣洩": ["發泄"],
    "皇族": ["貴族"],
    "邊個": ["誰"],
    "金黃色": ["金"],
    "兒子": ["仔"],
    "吵架": ["爭吵"],
    "看來": ["看似"],
    "保存": ["儲存"],
    "存貨": ["存量"],
    "一手": ["單手"],
    "手脚": ["肢體"],
    "水壺": ["壺"],
    "用力": ["使勁"],
    "眼利": ["好眼"],
    "服務員": ["服務台"],
    "休息": ["歇息"],
    "小組": ["分隊"],
    "沙拉": ["色拉"],
    "瘀傷": ["瘀青", "瘀血"],
    "刺青": ["文身"],
    "丟臉": ["羞恥", "羞家"],
    "轉學": ["轉校"],
    "出走": ["離家"],
    "單位": ["模組"],
    "兩個": ["兩枚"],
    "顛倒": ["翻轉"],
    "坐牢": ["入獄"],
    "騷": ["風騷"],
    "信仰": ["教派"],
    "節省": ["節約"],
    "我嘅": ["我的"],
    "搞到": ["弄到"],
    "所謂": ["可謂"],
    "它": ["牠"],
    "看穿": ["看透"],
    "緣分": ["因緣"],
    "會議": ["開會"],
    "項鍊": ["項鏈", "頸鏈"],
    "魚丸": ["魚圓"],
    "因此": ["所以"],
    "海內外": ["中外"],
    "全能": ["萬能", "多面手"],
    "傻瓜": ["傻子"],
    "無心": ["無意"],
    "權勢": ["勢力"],
    "商店": ["雜貨店"],
    "厲害": ["勁", "很強"],
    "母親": ["媽媽"],
    "居民": ["公民"],
    "偵探": ["警探"],
    "走路": ["行走"],
    "乾瞪眼": ["眼白白"],
    "等於": ["等同"],
    "背着": ["揹住"],
    "蘿蔔": ["蔔"],
    "製造": ["製作"],
    "指導": ["輔導"],
    "趕上": ["追及"],
    "翅膀": ["翼"],
    "量度": ["測度"],
    "版主": ["樓主"],
    "非常": ["十分"],
    "雌": ["母"],
    "合攏": ["合埋"],
    "幾乎": ["差唔多"],
    "好好地": ["乖乖"],
    "揹": ["背"],
    "零食": ["小吃"],
    "越來越": ["愈來愈"],
    "黎明": ["破曉"],
    "黃昏": ["日落"],
    "清澈": ["澄"],
    "雪糕": ["冰淇淋", "雪條"],
    "吉他": ["結他"],
    "翻去": ["翻開"],
    "識講嘢": ["識講"],
    "豬排": ["豬扒"],
    "跪下": ["跪"],
    "硬幣": ["銀幣", "錢幣"],
    "中學": ["高中"],
    "共同": ["共有"],
    "打字法": ["輸入"],
    "差不多": ["八九不離十"],
    "人民幣": ["人仔"],
    "起初": ["最初"],
    "勤奮": ["勤勞"],
    "嘀咕": ["喃喃自語"],
    "那裏": ["那邊"],
    "壞笑": ["陰笑"],
    "迫不及待": ["急不及待"],
    "拇指": ["大拇指"],
    "極其": ["極為"],
    "游泳": ["游水"],
    "公犬": ["狗"],
    "眯": ["瞇眼"],
    "綽號": ["外號"],
    "盡力": ["落力"],
    "馬鈴薯": ["土豆"],
    "變成": ["變為"],
    "邊度": ["邊間"],
    "亮燈": ["開燈"],
    "堪輿": ["風水"],
    "頭型": ["髮型"],
    "哄抬": ["炒賣"],
    "至愛": ["最喜歡"],
    "研究院": ["研究所"],
    "可以": ["做到"],
    "別人": ["旁人"],
    "一來": ["一嚟"],
    "侍應生": ["服務員"],
    "引起": ["勾起"],
    "反詰": ["反問"],
    "無意中": ["無意"],
    "安靜": ["寧靜"],
    "厭惡": ["討厭"],
    "早上": ["早晨"],
    "時髦": ["時尚"],
    "海洋館": ["水族館"],
    "黏土": ["粘土"],
    "倖存": ["生還者"],
    "的確": ["確實"],
    "茶室": ["餐廳", "飯店"],
    "脆片": ["薯條"],
}

FUNCTION = {
    "八月",
    "九月",
    "荃灣",
    "十點",
    "呱",
    "咖",
    "撻",
    "螯",
    "貢",
    "陰毛",
    "一本",
    "握手",
    "考研",
    "設計師",
    "冷汗",
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
        for ln in (FIXT / "syn_top5000_b06_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
        if ln.strip()
    ]
    assert len(heads) == 148, len(heads)

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

    # within-batch undirected dedupe (e.g. 鬧交/嗌交 both → 吵架)
    seen: set[tuple[str, str]] = set()
    rows: list[tuple[str, str]] = []
    for h, t in accepted.items():
        key = pair_undirected_key(h, t)
        if key in seen or key in existing:
            continue
        seen.add(key)
        rows.append((h, t))

    acc = {h for h, _ in rows}
    nn: OrderedDict[str, str] = OrderedDict()
    adq: list[tuple[str, str, str]] = []
    for h in heads:
        if h in acc:
            continue
        if normalize_literal(h) in covered:
            adq.append((h, "prior project_syn edge covers head", BATCH))
            continue
        if h in FUNCTION:
            nn[h] = "function_word"
        elif h in POLY:
            nn[h] = "polysemous_no_stable_sense"
        else:
            nn[h] = "no_stable_near_synonym"
    adq_h = {h for h, _, _ in adq}
    for h in heads:
        if h not in acc and h not in nn and h not in adq_h:
            nn[h] = "no_stable_near_synonym"

    assert len(acc) + len(nn) + len(adq_h) == 148, (len(acc), len(nn), len(adq_h))
    (FIXT / "syn_top5000_b06_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b06_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b06_adequate.tsv").write_text(
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
            "failed": failed[:12],
            "nn_heads": list(nn.keys())[:20],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
