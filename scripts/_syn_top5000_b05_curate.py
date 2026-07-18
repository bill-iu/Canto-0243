"""Curate syn_top5000 batch-5 fixtures."""
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
BATCH = "syn-top5000-b05-20260718"

RAW = {
    "差佬": "警察",
    "櫃桶": "抽屜",
    "晚晚": "每晚",
    "每晚": "夜夜",
    "理智": "理性",
    "秩序": "次序",
    "講聲": "出聲",
    "起嚟": "起來",
    "適應": "順應",
    "重啓": "重開",
    "分分鐘": "隨時",
    "初初": "起初",
    "加埋": "加上",
    "手套": "手襪",
    "手指尾": "指尖",
    "睇見": "看見",
    "落堂": "下課",
    "跑車": "賽車",
    "一天": "整天",
    "嗰晚": "當晚",
    "放榜": "公布",
    "樣衰": "難看",
    "沿途": "一路",
    "細粒": "細小",
    "膠布": "膠帶",
    "車仔": "小車",
    "偷食": "偷嘴",
    "專登": "故意",
    "恤衫": "襯衫",
    "樣貌": "容貌",
    "直行": "向前",
    "螢幕": "熒幕",
    "貨倉": "倉庫",
    "郵局": "郵政局",
    "接下來": "然後",
    "今時今日": "現在",
    "包住": "包起",
    "吸塵機": "吸塵器",
    "擺明": "明顯",
    "筷子": "箸",
    "聲線": "嗓音",
    "舖頭": "店舖",
    "那些": "嗰啲",
    "一般人": "普通人",
    "叫停": "制止",
    "巴士站": "車站",
    "得人驚": "可怕",
    "打人": "毆打",
    "攬實": "攬住",
    "有嘢": "有事",
    "死者": "死人",
    "牛油": "奶油",
    "神父": "牧師",
    "聽晚": "明晚",
    "話唔定": "說不定",
    "隨心": "隨意",
    "低聲": "小聲",
    "夾住": "夾緊",
    "好多人": "眾人",
    "新抱": "媳婦",
    "早知": "預料",
    "權利": "權益",
    "質素": "品質",
    "發貨": "出貨",
    "構建": "建立",
    "不再": "再不",
    "八卦": "傳聞",
    "八爪魚": "章魚",
    "制度": "體制",
    "可能性": "可能",
    "好多時": "經常",
    "收銀": "收款",
    "每人": "各人",
    "睡衣": "睡袍",
    "花灑": "花灑頭",
    "話事": "做主",
    "陪住": "陪伴",
    "世紀": "時代",
    "凳仔": "矮凳",
    "嘈交": "吵架",
    "因住": "小心",
    "埋位": "就座",
    "大隻佬": "大漢",
    "揹": "背",
    "收聲": "住口",
    "有講有笑": "談笑",
    "紅蘿蔔": "胡蘿蔔",
    "起勢": "用力",
    "醜樣": "醜陋",
    "門鐘": "門鈴",
    "鬆一口氣": "放心",
    "冷衫": "毛衣",
    "匿埋": "躲藏",
    "好耐": "好久",
    "廁紙": "手紙",
    "手錶": "手表",
    "捉實": "抓緊",
    "男神": "偶像",
    "直程": "簡直",
    "相識": "認識",
    "耳機": "耳筒",
    "近排": "最近",
    "除衫": "脫衣",
    "點睇": "看法",
    "補丁": "補釘",
    "三文治": "三明治",
    "執起": "拾起",
    "怪獸": "怪物",
    "打圈": "打轉",
    "殺人": "殺害",
    "毛蟲": "幼蟲",
    "無端端": "平白無故",
    "生仔": "生育",
    "草叢": "草莽",
    "落街": "出街",
    "負面": "消極",
    "過份": "過分",
    "審計": "稽核",
    "共鳴": "同感",
    "剩返": "剩下",
    "各種": "各樣",
    "回歸": "回來",
    "小矮人": "侏儒",
    "未夠": "不足",
    "立法": "制定",
    "總部": "總行",
    "閉上": "合攏",
    "傻佬": "傻瓜",
    "冇幾耐": "不久",
    "呷醋": "妒忌",
    "壓住": "按住",
    "望下": "看看",
}

ALTS = {
    "警察": ["差人", "警員"],
    "抽屜": ["櫃桶"],
    "每晚": ["夜夜"],
    "夜夜": ["每晚"],
    "理性": ["理智"],
    "次序": ["秩序"],
    "出聲": ["講"],
    "起來": ["起身"],
    "順應": ["遷就", "適合"],
    "重開": ["重新啟動", "重啓"],
    "隨時": ["隨時隨地"],
    "起初": ["最初"],
    "加上": ["加"],
    "手襪": ["手套"],
    "指尖": ["指頭"],
    "看見": ["見到"],
    "下課": ["落堂"],
    "賽車": ["跑車"],
    "整天": ["全日"],
    "當晚": ["嗰晚"],
    "公布": ["發表"],
    "難看": ["醜", "唔好睇"],
    "一路": ["沿路"],
    "細小": ["細"],
    "膠帶": ["膠紙"],
    "小車": ["車"],
    "偷嘴": ["偷食"],
    "故意": ["特登"],
    "襯衫": ["襯衣"],
    "容貌": ["相貌"],
    "向前": ["一直行", "直行"],
    "熒幕": ["屏幕", "顯示屏"],
    "倉庫": ["貨倉"],
    "郵政局": ["郵政"],
    "然後": ["跟着"],
    "現在": ["如今"],
    "包起": ["包紮", "包裹"],
    "吸塵器": ["吸塵"],
    "明顯": ["顯然"],
    "箸": ["筷子"],
    "嗓音": ["聲音", "嗓子"],
    "店舖": ["舖", "商店"],
    "嗰啲": ["那些"],
    "普通人": ["常人"],
    "制止": ["阻止"],
    "車站": ["巴士站"],
    "可怕": ["嚇人"],
    "毆打": ["揍"],
    "攬住": ["抱住"],
    "有事": ["有問題"],
    "死人": ["死屍"],
    "奶油": ["牛油"],
    "牧師": ["神父"],
    "明晚": ["聽晚"],
    "說不定": ["或許"],
    "隨意": ["隨便"],
    "小聲": ["細聲"],
    "夾緊": ["夾住"],
    "眾人": ["好多人"],
    "媳婦": ["新抱"],
    "預料": ["料到", "早知"],
    "權益": ["權利"],
    "品質": ["質量"],
    "出貨": ["發貨"],
    "建立": ["建構"],
    "再不": ["不再"],
    "傳聞": ["傳言"],
    "章魚": ["八爪魚"],
    "體制": ["制度"],
    "可能": ["或許"],
    "經常": ["常常"],
    "收款": ["收銀"],
    "各人": ["每人"],
    "睡袍": ["睡衣"],
    "花灑頭": ["花灑"],
    "做主": ["話事"],
    "陪伴": ["陪同"],
    "時代": ["百年"],
    "矮凳": ["板凳", "凳子"],
    "吵架": ["爭吵"],
    "小心": ["留意"],
    "就座": ["入座"],
    "大漢": ["大隻佬"],
    "背": ["揹"],
    "住口": ["咪嘈", "收聲"],
    "談笑": ["有講有笑"],
    "胡蘿蔔": ["紅蘿蔔"],
    "用力": ["使勁"],
    "醜陋": ["醜"],
    "門鈴": ["門鐘"],
    "放心": ["安心"],
    "毛衣": ["冷衫"],
    "躲藏": ["隱藏"],
    "好久": ["長久", "許久"],
    "手紙": ["紙巾"],
    "手表": ["錶", "腕表"],
    "抓緊": ["捉住"],
    "偶像": ["男神"],
    "簡直": ["完全"],
    "認識": ["相識"],
    "耳筒": ["耳塞"],
    "最近": ["近來"],
    "脫衣": ["除衫"],
    "看法": ["意見"],
    "補釘": ["修補"],
    "三明治": ["三文治"],
    "拾起": ["執起"],
    "怪物": ["妖怪"],
    "打轉": ["打圈"],
    "殺害": ["謀殺"],
    "幼蟲": ["毛蟲"],
    "平白無故": ["平白"],
    "生育": ["生產"],
    "草莽": ["草叢"],
    "出街": ["逛街"],
    "消極": ["差"],
    "過分": ["過度"],
    "稽核": ["審核"],
    "同感": ["共鳴"],
    "剩下": ["剩餘"],
    "各樣": ["各式"],
    "回來": ["返來"],
    "侏儒": ["小矮人"],
    "不足": ["不夠"],
    "制定": ["立法"],
    "總行": ["總部"],
    "合攏": ["合埋"],
    "傻瓜": ["傻子", "笨蛋"],
    "不久": ["冇耐"],
    "妒忌": ["嫉妒"],
    "按住": ["壓住"],
    "看看": ["睇下"],
}

FUNCTION = {
    "巴膠",
    "情人節",
    "臭狐",
    "不出",
    "啡",
    "射出",
    "得滯",
    "摑",
    "收線",
    "柒頭",
    "迴",
    "右上",
    "兩點",
    "嬴",
    "雞雞",
    "另一",
    "捨",
    "點呢",
    "多得",
    "眼甘甘",
    "關我事",
    "一如",
    "下低",
    "佈",
    "前便",
    "十二點",
    "喥",
    "嗰次",
    "靚靚",
    "車型",
    "琳",
    "老味",
    "長得",
    "兩下",
    "得切",
    "直落",
    "虧佬",
    "麻甩佬",
    "下便",
    "不知幾",
    "唔多唔少",
    "蛋蛋",
    "阿麗",
    "九龍",
    "人嚟",
    "咕",
    "扐",
    "打畀",
    "搖搖板",
    "沙沙",
    "眼定定",
    "口交",
    "叮叮",
    "啤住",
    "昇",
    "肥妹",
    "話費",
    "文件夾",
}

POLY = {
    "深處",
    "絲襪",
    "酒精",
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
        for ln in (FIXT / "syn_top5000_b05_heads.tsv").read_text(encoding="utf-8").splitlines()[1:]
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

    assert len(acc) + len(nn) + len(adq_h) == 200, (len(acc), len(nn), len(adq_h))
    (FIXT / "syn_top5000_b05_accepted.tsv").write_text(
        "head\ttail\n" + "\n".join(f"{h}\t{t}" for h, t in rows) + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b05_no_natural.tsv").write_text(
        "head\treason\tbatch_id\n"
        + "\n".join(f"{h}\t{r}\t{BATCH}" for h, r in nn.items())
        + "\n",
        encoding="utf-8",
    )
    (FIXT / "syn_top5000_b05_adequate.tsv").write_text(
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
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
