"""Curate syn_top5000 batch-2 fixtures (membership-checked)."""
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
BATCH = "syn-top5000-b02-20260718"

# head -> preferred tail (will fallback via ALTS)
RAW: dict[str, str] = {
    "無人": "沒人",
    "只不過": "只是",
    "耳仔": "耳朵",
    "條女": "女孩",
    "拍拖": "戀愛",
    "點鐘": "鐘點",
    "屋企人": "家人",
    "核突": "難看",
    "對面": "對門",
    "琴晚": "昨晚",
    "坐低": "坐下",
    "講真": "說實話",
    "細細聲": "小聲",
    "腦海": "腦際",
    "機場": "飛機場",
    "有事": "出事",
    "琴日": "昨天",
    "指住": "指住",
    "細個": "小時候",
    "乜嘢": "什麼",
    "天晴": "晴天",
    "熊仔": "小熊",
    "陣間": "待會兒",
    "對話": "會話",
    "有人": "某人",
    "麵包": "麪包",
    "再講": "再說",
    "梳化": "沙發",
    "你好": "您好",
    "答案": "答覆",
    "第二個": "另一個",
    "伸出": "伸手",
    "有沒有": "是否有",
    "上嚟": "上來",
    "師兄": "師弟",
    "讚": "稱讚",
    "傾計": "聊天",
    "屬於": "屬",
    "特登": "故意",
    "裡面": "裏面",
    "課室": "教室",
    "碟": "碟子",
    "講緊": "在說",
    "紙巾": "面紙",
    "落嚟": "下來",
    "唔多": "不多",
    "唔錯": "不錯",
    "馬騮": "猴子",
    "留低": "留下",
    "再見": "再會",
    "嗰陣": "那時",
    "裏便": "裏面",
    "畀人": "被人",
    "大嗌": "大叫",
    "總係": "總是",
    "仲未": "尚未",
    "姊妹": "姐妹",
    "阿叔": "叔叔",
    "打電話": "通話",
    "搞掂": "辦妥",
    "人哋": "人家",
    "盡量": "儘量",
    "視頻": "影片",
    "枕頭": "枕",
    "冇問題": "沒問題",
    "嗰時": "那時",
    "影相": "拍照",
    "第一次": "首次",
    "細聲": "小聲",
    "等陣": "稍等",
    "失望": "沮喪",
    "行埋": "走近",
    "埋嚟": "過來",
    "生果": "水果",
    "幾耐": "多久",
    "聽過": "聽聞",
    "衰人": "壞人",
    "提子": "葡萄",
    "傻仔": "傻瓜",
    "唔舒服": "難受",
    "好靚": "漂亮",
    "條友": "傢伙",
    "消防員": "救火員",
    "銀包": "錢包",
    "狗仔": "小狗",
    "香蕉": "蕉",
    "橙汁": "果汁",
    "講笑": "開玩笑",
    "拖鞋": "涼鞋",
    "打機": "遊戲",
    "就快": "快要",
    "石頭": "石",
    "第二日": "翌日",
    "擰轉": "轉動",
    "將會": "即將",
    "氹": "哄",
    "醉": "醺",
    "雀仔": "小鳥",
    "夠膽": "大膽",
    "請問": "試問",
    "講下": "談談",
    "後便": "後面",
    "兔仔": "兔子",
    "會話": "對話",
    "匙羹": "湯匙",
    "朝早": "早上",
    "食嘢": "進食",
    "拳頭": "拳",
    "諗法": "想法",
    "雞蛋": "蛋",
    "每日": "每天",
    "大把": "很多",
    "大脾": "大腿",
    "差啲": "差點",
    "求其": "隨便",
    "直頭": "簡直",
    "睇落": "看來",
    "車站": "火車站",
    "呻吟": "哼",
    "收埋": "隱藏",
    "故仔": "故事",
    "嚟到": "來到",
    "相機": "照相機",
    "回復": "回覆",
    "不嬲": "一向",
    "笑笑口": "微笑",
    "好味": "美味",
    "算了": "罷了",
    "表白": "剖白",
    "凳": "凳子",
    "尿": "小便",
    "視線": "目光",
    "社會": "世上",
    "畫面": "影像",
    "地圖": "圖紙",
    "目的": "目標",
    "自信": "信心",
    "音樂": "歌曲",
    "科技": "技術",
    "印象": "感覺",
    "鬆": "放鬆",
    "班主任": "老師",
    "港人": "香港人",
    "博客": "網誌",
    "蝦": "蝦子",
    "桶": "水桶",
    "舖": "店舖",
    "迷宮": "迷陣",
}

ALTS: dict[str, list[str]] = {
    "沒人": ["無人"],
    "只是": ["僅僅", "不過"],
    "耳朵": ["耳"],
    "女孩": ["姑娘", "女生"],
    "戀愛": ["談戀愛", "約會"],
    "鐘點": ["時刻", "時辰"],
    "家人": ["親人", "家屬"],
    "難看": ["醜陋", "醜"],
    "對門": ["對面"],
    "昨晚": ["昨夜", "隔晚"],
    "坐下": ["坐"],
    "說實話": ["坦白", "老實說"],
    "小聲": ["輕聲", "細聲"],
    "腦際": ["腦子", "腦中"],
    "飛機場": ["空港"],
    "出事": ["有事"],
    "昨天": ["昨日", "隔日"],
    "指住": ["指著", "指向"],
    "小時候": ["幼時", "童年"],
    "什麼": ["甚麼", "何事"],
    "晴天": ["晴朗"],
    "小熊": ["熊"],
    "待會兒": ["等會", "等陣"],
    "會話": ["交談", "對話"],
    "某人": ["有的人"],
    "麪包": ["麵包"],
    "再說": ["另外"],
    "沙發": ["沙發椅"],
    "您好": ["你好"],
    "答覆": ["答案", "回應"],
    "另一個": ["其它", "別個"],
    "伸手": ["伸出"],
    "是否有": ["有無", "是否"],
    "上來": ["上"],
    "師弟": ["師兄"],
    "稱讚": ["讚美", "誇"],
    "聊天": ["談話", "閒聊"],
    "屬": ["隸屬"],
    "故意": ["特意", "存心"],
    "裏面": ["內部", "裡頭"],
    "教室": ["課堂"],
    "碟子": ["盤子"],
    "在說": ["說著"],
    "面紙": ["紙巾"],
    "下來": ["下"],
    "不多": ["少"],
    "不錯": ["很好"],
    "猴子": ["猿猴"],
    "留下": ["留"],
    "再會": ["再見"],
    "那時": ["當時", "彼時"],
    "被人": ["遭人"],
    "大叫": ["喊叫", "呼叫"],
    "總是": ["老是", "一直"],
    "尚未": ["還沒", "仍未"],
    "姐妹": ["姊妹"],
    "叔叔": ["叔父"],
    "通話": ["致電"],
    "辦妥": ["完成", "搞定"],
    "人家": ["別人"],
    "儘量": ["盡力"],
    "影片": ["錄像", "短片"],
    "枕": ["枕頭"],
    "沒問題": ["無事", "無妨"],
    "拍照": ["攝影", "照相"],
    "首次": ["頭一次"],
    "稍等": ["等一下", "等陣"],
    "沮喪": ["灰心", "失落"],
    "走近": ["靠近"],
    "過來": ["來"],
    "水果": ["鮮果"],
    "多久": ["多長"],
    "聽聞": ["聽說"],
    "壞人": ["惡人"],
    "葡萄": ["提子"],
    "傻瓜": ["笨蛋", "傻子"],
    "難受": ["不適"],
    "漂亮": ["美麗", "靚"],
    "傢伙": ["家伙"],
    "救火員": ["消防"],
    "錢包": ["錢袋"],
    "小狗": ["犬"],
    "蕉": ["芭蕉"],
    "果汁": ["橙汁"],
    "開玩笑": ["玩笑"],
    "玩笑": ["開玩笑"],
    "涼鞋": ["拖鞋"],
    "遊戲": ["電玩"],
    "快要": ["即將"],
    "石": ["石頭"],
    "翌日": ["次日"],
    "轉動": ["旋轉"],
    "即將": ["將要"],
    "哄": ["逗"],
    "醺": ["醉"],
    "小鳥": ["鳥"],
    "大膽": ["勇敢"],
    "試問": ["請問"],
    "談談": ["說說"],
    "後面": ["后方", "後邊"],
    "兔子": ["兔"],
    "對話": ["會話", "交談"],
    "湯匙": ["勺子", "匙"],
    "早上": ["早晨"],
    "進食": ["吃東西"],
    "拳": ["拳頭"],
    "想法": ["主意", "念頭"],
    "蛋": ["雞蛋"],
    "每天": ["天天"],
    "很多": ["許多"],
    "大腿": ["腿"],
    "差點": ["幾乎"],
    "隨便": ["任意"],
    "簡直": ["完全"],
    "看來": ["看起來"],
    "火車站": ["車站"],
    "哼": ["呻"],
    "隱藏": ["藏"],
    "故事": ["傳奇"],
    "來到": ["抵達"],
    "照相機": ["攝影機"],
    "回覆": ["回答", "答覆"],
    "一向": ["從來"],
    "微笑": ["笑"],
    "美味": ["好吃"],
    "罷了": ["算啦"],
    "剖白": ["表白"],
    "凳子": ["椅子"],
    "小便": ["尿"],
    "目光": ["眼光"],
    "世上": ["世間"],
    "影像": ["圖像"],
    "圖紙": ["地圖"],
    "目標": ["目的"],
    "信心": ["自信心"],
    "歌曲": ["歌"],
    "技術": ["科技"],
    "感覺": ["感受"],
    "放鬆": ["鬆弛"],
    "老師": ["教師"],
    "牙粉": ["牙膏"],
    "香港人": ["港人"],
    "社會工作者": ["社工"],
    "網誌": ["部落格"],
    "蝦子": ["蝦"],
    "水桶": ["桶"],
    "店": ["商店"],
    "咖啡茶": ["咖啡"],
    "琉璃": ["玻璃"],
    "迷陣": ["迷宮"],
    "網域": ["域名"],
    "佰": ["百"],
    "會面": ["見面"],
}

FUNCTION = {
    "呢種",
    "一片",
    "一步",
    "幾日",
    "一眼",
    "點都",
    "嚟講",
    "點呀",
    "點啊",
    "嚟㗎",
    "嘅話",
    "得多",
    "上便",
    "裡",
    "將我",
    "多嘢",
    "正正",
    "一場",
    "啵",
    "嗄",
    "碌",
    "入到",
    "邊有",
    "幾咁",
    "吔",
    "咭",
    "多個",
    "孖",
    "曱",
    "甴",
    "紮",
    "他們",
    "百",
}

POLY = {
    "錶",
    "玻璃",
    "咖啡",
    "迷宮",
    "域名",
    "博客",
    "鏈接",
    "頁面",
    "結界",
    "甲蟲",
    "狼",
    "盆",
    "桶",
    "蝦",
    "牙膏",
    "帖子",
    "舖",
    "尿",
    "蕉",
}


def pick_tail(head: str, preferred: str, lex: set[str]) -> str | None:
    cands = [preferred, *ALTS.get(preferred, [])]
    hn = normalize_literal(head)
    for c in cands:
        n = normalize_literal(c)
        if n and n in lex and n != hn:
            return n
    return None


def main() -> int:
    lex = load_lexicon_literals()
    heads = [
        ln.split("\t")[1]
        for ln in (FIXT / "syn_top5000_b02_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
        if ln.strip()
    ]

    accepted: OrderedDict[str, str] = OrderedDict()
    failed: list[tuple[str, str]] = []
    for h, t in RAW.items():
        if h not in heads:
            continue
        if t == h or t == "天使":
            continue
        if h in {"他們"}:  # gender swap not syn
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

    for h, _ in failed:
        if h not in accepted and h not in nn and h in heads:
            nn[h] = "no_stable_near_synonym"

    for h in heads:
        if h not in accepted and h not in nn:
            nn[h] = "no_stable_near_synonym"

    assert len(accepted) + len(nn) == 200, (len(accepted), len(nn))

    (FIXT / "syn_top5000_b02_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in accepted.items()) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b02_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b02_adequate.tsv").write_text("head\tnote\n", encoding="utf-8")

    print(
        {
            "accepted": len(accepted),
            "nn": len(nn),
            "nn_reasons": dict(Counter(nn.values())),
            "failed_pick": failed[:25],
            "failed_n": len(failed),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
