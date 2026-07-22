"""Curate syn_top5000 batch-3 fixtures."""
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
from ingest.project_synonyms import load_lexicon_literals  # noqa: E402

FIXT = ROOT / "data" / "syn_ant" / "project" / "fixtures"
BATCH = "syn-top5000-b03-20260718"

RAW: dict[str, str] = {
    "下個": "下一個",
    "唔怪得": "怪不得",
    "明知": "清楚",
    "粗口": "髒話",
    "估到": "猜到",
    "仲好": "還好",
    "做嘢": "做事",
    "公主": "皇女",
    "數據庫": "資料庫",
    "好朋友": "好友",
    "看更": "守衛",
    "落車": "下車",
    "細路仔": "小孩",
    "西瓜": "瓜",
    "冇用": "無用",
    "表哥": "表兄",
    "在線": "線上",
    "水喉": "水龍頭",
    "無謂": "何必",
    "開學": "開課",
    "夠鐘": "到時",
    "天台": "屋頂",
    "橙色": "橘色",
    "別的": "其他",
    "老細": "老闆",
    "面紅": "臉紅",
    "電視機": "電視",
    "冇嘢": "沒事",
    "阻住": "擋住",
    "隨住": "隨著",
    "入嚟": "進來",
    "還有": "另外",
    "嘢食": "食物",
    "這裡": "這兒",
    "即可": "便可",
    "好返": "好轉",
    "八婆": "長舌婦",
    "第日": "他日",
    "返轉頭": "回頭",
    "吹水": "閒聊",
    "怕醜": "害羞",
    "換衫": "換衣服",
    "洗頭水": "洗髮水",
    "點做": "怎麼辦",
    "用於": "用來",
    "大部份": "大部分",
    "心裡": "心裏",
    "聖誕老人": "聖誕老公公",
    "遲啲": "稍後",
    "小弟": "弟弟",
    "肥仔": "胖子",
    "筆記本": "記事本",
    "就嚟": "快要",
    "背影": "身影",
    "好嘢": "好事",
    "幾點": "何時",
    "發夢": "做夢",
    "不知": "不清楚",
    "搞笑": "好笑",
    "擰頭": "搖頭",
    "最大": "最大",
    "仔女": "兒女",
    "傻妹": "傻姑娘",
    "唔捨得": "捨不得",
    "按摩": "推拿",
    "朝頭早": "清晨",
    "老嘢": "老人",
    "蝴蝶": "蝶",
    "衰仔": "壞小子",
    "校車": "公車",
    "風車": "風輪",
    "冇所謂": "無所謂",
    "大隻": "高大",
    "並無": "沒有",
    "千祈": "千萬",
    "尋晚": "昨晚",
    "直情": "簡直",
    "衣櫃": "衣櫥",
    "不在": "不在場",
    "交流": "溝通",
    "太過": "過於",
    "紫色": "紫",
    "總有": "終有",
    "是但": "隨便",
    "確定": "肯定",
    "間房": "房間",
    "忘了": "忘記",
    "之餘": "此外",
    "沿住": "沿著",
    "文檔": "文件",
    "好少": "很少",
    "寵物": "愛畜",
    "以嚟": "以來",
    "停低": "停下",
    "叫醒": "喚醒",
    "師奶": "主婦",
    "體力": "氣力",
    "嘴角": "口角",
    "後尾": "後來",
    "眼中": "眼裏",
    "行山": "登山",
    "接住": "接著",
    "合照": "合影",
    "貓仔": "小貓",
    "太大": "過大",
    "打橫": "橫過",
    "玩完": "結束",
    "長大": "成長",
    "阿伯": "伯父",
    "忍者": "隱者",
    "放假": "休假",
    "數字": "數目",
    "狐狸": "狐",
    "盡快": "趕快",
    "糖水": "甜湯",
    "角色": "人物",
    "越嚟越": "越來越",
    "什麼時候": "何時",
    "墳場": "墓地",
    "廣告": "宣傳",
    "間中": "偶爾",
    "電梯": "升降機",
    "瀑布": "飛瀑",
    "行街": "逛街",
    "講起": "提起",
    "鴨仔": "小鴨",
    "事發": "發生",
    "唸": "念",
    "大小姐": "小姐",
    "礦場": "礦坑",
    "空姐": "空中小姐",
    "第時": "將來",
    "時尚": "潮流",
    "轉載": "轉發",
    "心痛": "傷心",
    "晏晝": "下午",
    "本能": "天性",
    "講乜": "說什麼",
    "雞仔": "小雞",
    "節目": "欄目",
    "乳頭": "奶頭",
    "橙色": "橘",
    "舐": "舔",
    "搓": "揉",
    "扁": "平",
    "嘟": "鳴",
    "箭": "矢",
    "舔": "舐",
    "陰道": "產道",
    "書包": "袋",
}

ALTS: dict[str, list[str]] = {
    "下一個": ["下個"],
    "怪不得": ["難怪"],
    "清楚": ["明白"],
    "髒話": ["穢語"],
    "猜到": ["料到"],
    "還好": ["幸好"],
    "做事": ["幹事", "工作"],
    "皇女": ["公主"],
    "資料庫": ["數據庫"],
    "好友": ["摯友", "密友"],
    "守衛": ["門衛", "保安"],
    "下車": ["落車"],
    "小孩": ["孩子", "細路"],
    "瓜": ["西瓜"],
    "無用": ["沒用"],
    "表兄": ["表哥"],
    "線上": ["網上"],
    "水龍頭": ["水喉"],
    "何必": ["不用"],
    "開課": ["開學"],
    "到時": ["屆時"],
    "屋頂": ["樓頂"],
    "橘色": ["橙"],
    "橘": ["橙"],
    "其他": ["其餘"],
    "老闆": ["上司"],
    "臉紅": ["緋紅"],
    "電視": ["電視機"],
    "沒事": ["無事"],
    "擋住": ["阻礙"],
    "隨著": ["跟着", "跟著"],
    "進來": ["入來"],
    "另外": ["此外"],
    "食物": ["食品"],
    "這兒": ["這裏", "這邊"],
    "便可": ["就可以"],
    "好轉": ["好起來"],
    "長舌婦": ["長舌"],
    "他日": ["改日"],
    "回頭": ["回轉"],
    "閒聊": ["聊天"],
    "害羞": ["腼腆", "靦腆"],
    "換衣服": ["更衣"],
    "洗髮水": ["洗髮露"],
    "怎麼辦": ["如何"],
    "用來": ["用作"],
    "大部分": ["多數"],
    "心裏": ["心中"],
    "聖誕老公公": ["聖誕老人"],
    "稍後": ["待會兒", "等陣"],
    "弟弟": ["弟"],
    "胖子": ["胖小子"],
    "記事本": ["記事簿", "簿"],
    "快要": ["即將"],
    "身影": ["影子"],
    "好事": ["好消息"],
    "何時": ["幾點鐘"],
    "做夢": ["夢"],
    "不清楚": ["不明"],
    "好笑": ["滑稽"],
    "搖頭": ["擺頭"],
    "兒女": ["子女"],
    "傻姑娘": ["傻女"],
    "捨不得": ["不捨"],
    "推拿": ["按摩"],
    "清晨": ["清早", "早上"],
    "老人": ["長者"],
    "蝶": ["蝴蝶"],
    "壞小子": ["壞蛋"],
    "公車": ["巴士"],
    "風輪": ["風車"],
    "無所謂": ["沒所謂"],
    "高大": ["魁梧"],
    "沒有": ["無"],
    "千萬": ["務必"],
    "昨晚": ["昨夜"],
    "簡直": ["完全"],
    "衣櫥": ["衣櫃"],
    "不在場": ["缺席"],
    "溝通": ["來往"],
    "過於": ["太"],
    "紫": ["紫色"],
    "終有": ["總會"],
    "隨便": ["任意"],
    "肯定": ["確認"],
    "房間": ["室"],
    "忘記": ["忘掉"],
    "此外": ["另外"],
    "沿著": ["順着", "順著"],
    "文件": ["檔案"],
    "很少": ["甚少"],
    "愛畜": ["寵物"],
    "以來": ["起"],
    "停下": ["停止"],
    "喚醒": ["吵醒"],
    "主婦": ["家庭主婦"],
    "氣力": ["力氣"],
    "口角": ["嘴邊"],
    "後來": ["其後"],
    "眼裏": ["眼裡", "眼內"],
    "登山": ["爬山"],
    "接著": ["然後"],
    "合影": ["拍照"],
    "小貓": ["貓"],
    "過大": ["偏大"],
    "橫過": ["橫行"],
    "結束": ["完結"],
    "成長": ["成年"],
    "伯父": ["伯伯"],
    "隱者": ["忍者"],
    "休假": ["放假"],
    "數目": ["數字"],
    "狐": ["狐狸"],
    "趕快": ["盡速"],
    "甜湯": ["糖水"],
    "人物": ["角色"],
    "越來越": ["愈來愈"],
    "墓地": ["墳地"],
    "宣傳": ["廣告"],
    "偶爾": ["間或"],
    "升降機": ["電梯"],
    "飛瀑": ["瀑布"],
    "逛街": ["散步"],
    "提起": ["談到"],
    "小鴨": ["鴨"],
    "發生": ["出現"],
    "念": ["讀"],
    "小姐": ["姑娘"],
    "礦坑": ["礦山"],
    "空中小姐": ["空姐"],
    "將來": ["未來"],
    "潮流": ["流行"],
    "轉發": ["轉貼"],
    "傷心": ["悲痛"],
    "下午": ["午後"],
    "天性": ["本性"],
    "說什麼": ["講什麼"],
    "小雞": ["雞"],
    "欄目": ["節目"],
    "奶頭": ["乳頭"],
    "舔": ["舐"],
    "舐": ["舔"],
    "揉": ["搓"],
    "平": ["扁"],
    "鳴": ["響"],
    "矢": ["箭"],
    "產道": ["陰道"],
}

FUNCTION = {
    "呯",
    "唔知幾",
    "幾次",
    "一嘢",
    "摺",
    "依種",
    "冇得",
    "你估",
    "曳曳",
    "係噉",
    "啤",
    "黐",
    "一堆",
    "嘅樣",
    "焗",
    "鬚",
    "厠",
    "蕹",
    "咁上下",
    "我識",
    "左上",
    "羹",
    "電芯",
    "呢排",
    "咔",
    "嗰種",
    "証",
    "唔切",
    "晞",
    "一排",
    "成身",
    "捽",
    "一套",
    "吋",
    "偈",
    "慾",
    "頁",
    "戇",
    "摷",
    "噏",
    "就好",
    "曚",
    "柯南",
    "你們",
    "得過",
    "做愛",
    "植入",
    "個月",
    "麪",
    "旺角",
    "淫賤",
    "魚排",
}

POLY = {
    "乳頭",
    "舐",
    "舔",
    "搓",
    "扁",
    "嘟",
    "箭",
    "陰道",
    "橙色",
    "紫色",
    "西瓜",
    "蝴蝶",
    "風車",
    "狐狸",
    "瀑布",
    "數字",
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
        for ln in (FIXT / "syn_top5000_b03_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
        if ln.strip()
    ]

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

    # undirected dedupe
    seen: set[tuple[str, str]] = set()
    deduped: OrderedDict[str, str] = OrderedDict()
    for h, t in accepted.items():
        key = pair_undirected_key(h, t)
        if key in seen:
            continue
        seen.add(key)
        deduped[h] = t
    accepted = deduped

    nn: OrderedDict[str, str] = OrderedDict()
    for h in heads:
        if h in accepted:
            continue
        if h in FUNCTION:
            nn[h] = "function_word"
        elif h in POLY:
            nn[h] = "polysemous_no_stable_sense"
        else:
            nn[h] = "no_stable_near_synonym"

    for h in heads:
        if h not in accepted and h not in nn:
            nn[h] = "no_stable_near_synonym"

    assert len(accepted) + len(nn) == 200, (len(accepted), len(nn))

    (FIXT / "syn_top5000_b03_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in accepted.items()) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b03_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b03_adequate.tsv").write_text("head\tnote\n", encoding="utf-8")
    print(
        {
            "accepted": len(accepted),
            "nn": len(nn),
            "reasons": dict(Counter(nn.values())),
            "failed_n": len(failed),
            "failed_sample": failed[:20],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
