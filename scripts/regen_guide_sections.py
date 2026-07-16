"""Generate guide SECTIONS with explain-synced labels; splice into guide-i18n.mjs."""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.services.query_explain import explain_query

REPO = Path(__file__).resolve().parents[1]

# (id, group, zh_title, zh_intro, en_title, en_intro, [(query, mode), ...])
SECTIONS_SPEC = [
    (
        "basic",
        "common",
        "基本查詢",
        "漢字、詞語、394052 碼或粵拼。",
        "Basic lookup",
        "Chinese characters, words, 394052 codes, or Jyutping.",
        [("香港", "m1"), ("nei hou", "m1"), ("ming4 baak6", "m1")],
    ),
    (
        "digit",
        "common",
        "0243 / 02493 / 394052 數字",
        "純數字搵同碼詞條；02493 分清二聲；394052 六聲碼三／五聲分明。",
        "0243 / 02493 / 394052 digits",
        "Digits only: find entries sharing the code; 02493 separates the second tone; 394052 6-tone codes keep tones 3 and 5 distinct.",
        [("23", "m1"), ("93", "m2"), ("45", "m3")],
    ),
    (
        "equals",
        "common",
        "同韻／同聲（=）",
        "字後面加 <code translate=\"no\">=</code> → 同韻；字前面加 <code translate=\"no\">=</code> → 同聲。可整詞用，亦可數字夾住一個字同時規定聲調。參考字唔一定出現喺結果。",
        "Same rhyme / initial (=)",
        "Put <code translate=\"no\">=</code> after a character for rhyme; before it for initial. Works on a whole word, or with tone digits around one character. The reference character need not appear in results.",
        [
            ("香=", "m1"),
            ("香=?", "m1"),
            ("?=香", "m1"),
            ("香港=", "m1"),
            ("=香港", "m1"),
            ("2我=3", "m1"),
            ("2=我3", "m1"),
            ("?+香=", "m1"),
        ],
    ),
    (
        "mask",
        "common",
        "有啲字限定、有啲留空",
        "定實你要嘅漢字或聲調數字；唔知嘅位用 <code translate=\"no\">?</code>／<code translate=\"no\">_</code>／<code translate=\"no\">%</code>（三個一樣）。開頭嘅 <code translate=\"no\">+</code> 可以唔打。",
        "Lock some characters, leave others open",
        "Set the characters or tone digits you need; fill unknowns with <code translate=\"no\">?</code> / <code translate=\"no\">_</code> / <code translate=\"no\">%</code> (all the same). A leading <code translate=\"no\">+</code> is optional.",
        [
            ("+香??", "m1"),
            ("?+你?", "m1"),
            ("_識_", "m1"),
            ("3_", "m1"),
            ("23?", "m1"),
            ("門0", "m1"),
        ],
    ),
    (
        "plus",
        "common",
        "用 + 加長或標明位置",
        "用 <code translate=\"no\">+</code> 加多一個字，或者標明邊個位置。<code translate=\"no\">字=</code>＝同韻；<code translate=\"no\">+=字</code>＝同聲；冇 <code translate=\"no\">=</code> 就係要呢個字本身。打 <code translate=\"no\">*</code> 等同 <code translate=\"no\">+</code>。",
        "Use + to lengthen or mark a position",
        "Use <code translate=\"no\">+</code> to add a character or mark a position. <code translate=\"no\">char=</code> = same rhyme; <code translate=\"no\">+=char</code> = same initial; without <code translate=\"no\">=</code> that exact character is required. <code translate=\"no\">*</code> works like <code translate=\"no\">+</code>.",
        [
            ("23@手", "m1"),
            ("23+好", "m1"),
            ("23+好=", "m1"),
            ("23+=好", "m1"),
            ("2+好3", "m1"),
            ("2+好=3", "m1"),
            ("+門0", "m1"),
            ("+門=0", "m1"),
        ],
    ),
    (
        "multi",
        "advanced",
        "多重同韻／同聲",
        "用數字規定聲調，用參考字規定同韻或同聲；可用 <code translate=\"no\">?</code> 留空某個字，或令第一個字任意、其餘跟某詞逐字同韻／同聲。",
        "Multi-slot rhyme / initial",
        "Use digits for tone codes and reference characters for rhyme or initial; leave a slot open with <code translate=\"no\">?</code>, or free the first character while the rest follow a sample word.",
        [
            ("23香=", "m1"),
            ("04困=49倒=", "m1"),
            ("04=困49=倒", "m1"),
            ("?4困=4潦=9倒=", "m1"),
            ("?3人=?", "m1"),
            ("窮?潦倒=", "m1"),
            ("窮困?倒=", "m1"),
            ("=窮?潦倒", "m1"),
            ("=窮困?倒", "m1"),
            ("?香港=", "m1"),
            ("?困潦倒=", "m1"),
            ("?=困潦倒", "m1"),
        ],
    ),
    (
        "wildcard-code",
        "advanced",
        "任意字＋數字碼＋尾字同韻",
        "開頭用 <code translate=\"no\">?</code> 表示第一個字隨便，再打聲調數字；最後一個漢字決定尾字要同邊個同韻。想再多一個字就加 <code translate=\"no\">+</code>。",
        "Any char + tone digits + last rhymes",
        "Leading <code translate=\"no\">?</code> leaves the first character open, then tone digits; the last character sets the rhyme for the end. Add <code translate=\"no\">+</code> for one more character.",
        [("?30人", "m1"), ("?30+人", "m1")],
    ),
    (
        "jyutping-anchor",
        "advanced",
        "用粵拼指定某個字",
        "唔想打漢字參考字時，可以用粵拼字母標明某個字嘅韻母、完整音節或聲母；位置之間用 <code translate=\"no\">+</code>（如 <code translate=\"no\">?+hon</code>、<code translate=\"no\">3+ngo4</code>）。",
        "Specify a syllable with Jyutping",
        "Instead of a Chinese reference character, type Jyutping letters for a final, full syllable, or initial; join positions with <code translate=\"no\">+</code> (e.g. <code translate=\"no\">?+hon</code>, <code translate=\"no\">3+ngo4</code>).",
        [
            ("?+hon", "m1"),
            ("?+yut?", "m1"),
            ("?+syut?", "m1"),
            ("3+ngo4", "m1"),
            ("3hon4", "m1"),
            ("3$漢4", "m1"),
            ("3h4", "m1"),
            ("3gw4", "m1"),
            ("23o", "m1"),
            ("23+o", "m1"),
            ("23ei0", "m1"),
            ("?+m?", "m1"),
            ("3m4", "m1"),
        ],
    ),
    (
        "ping-ze",
        "advanced",
        "平仄（平／仄）",
        "<code translate=\"no\">P</code>＝平、<code translate=\"no\">Z</code>＝仄；數字＝嗰個字要同呢個聲調同音。平仄模式下可喺搜尋欄下切換 <strong>0243</strong>／<strong>02493</strong>／<strong>394052</strong>；P／Z 一律按六聲判定。",
        "Ping / ze pattern",
        "<code translate=\"no\">P</code> = ping, <code translate=\"no\">Z</code> = ze; a digit means that character must match that tone. In ping–ze mode, pick <strong>0243</strong> / <strong>02493</strong> / <strong>394052</strong> under the search box; P/Z always use the 6-tone scale.",
        [("PZ", "pz"), ("PZ3", "pz"), ("PZ好=", "pz"), ("=好PZ", "pz")],
    ),
    (
        "relation",
        "advanced",
        "近義 / 反義",
        "<code translate=\"no\">~</code> 近義、<code translate=\"no\">!</code> 反義；可加碼前綴。僅 0243搜尋三檔（唔包括近反義模式）。",
        "Synonym / antonym",
        "<code translate=\"no\">~</code> near-synonym, <code translate=\"no\">!</code> antonym; optional code prefix. 0243 search tiers only (not synonym/antonym mode).",
        [("~開心", "m1"), ("!苦悶", "m1"), ("33!開心", "m1")],
    ),
    (
        "syn-pool",
        "advanced",
        "近反義模式（瀏覽相關詞）",
        "切換近反義模式，打一個詞就列出近義、反義同相關詞。",
        "Synonym/antonym mode (browse related words)",
        "Switch to synonym/antonym mode and type a word to list near-synonyms, antonyms, and related words.",
        [("開心", "syn")],
    ),
    (
        "compound-syn",
        "advanced",
        "近義複合詞",
        "<code translate=\"no\">~~</code> 搵二字近義複合；可加碼前綴或尾韻字。",
        "Near-synonym compounds",
        "<code translate=\"no\">~~</code> finds two-character near-synonym compounds; optional code prefix or trailing rhyme character.",
        [("~~", "m1"), ("33~~", "m1"), ("~~你", "m1"), ("33~~你", "m1")],
    ),
    (
        "compound-ant",
        "advanced",
        "反義複合詞",
        "<code translate=\"no\">!!</code> 搵二字反義複合；可加碼前綴或尾韻字。",
        "Antonym compounds",
        "<code translate=\"no\">!!</code> finds two-character antonym compounds; optional code prefix or trailing rhyme character.",
        [("!!", "m1"), ("33!!", "m1"), ("!!你", "m1"), ("33!!你", "m1")],
    ),
    (
        "doubled",
        "advanced",
        "雙聲疊韻字",
        "連續 <code translate=\"no\">$</code> 的個數 = 詞長（2–4）；各字音節相同（聲調不限）；可加碼前綴或尾韻字。語法鏡像 <code translate=\"no\">~~</code>。",
        "Reduplicated same-syllable words",
        "Count of consecutive <code translate=\"no\">$</code> = word length (2–4); each character shares the same syllable (any tone); optional code prefix or trailing rhyme char. Syntax mirrors <code translate=\"no\">~~</code>.",
        [
            ("$$", "m1"),
            ("$$$", "m1"),
            ("$$$$", "m1"),
            ("33$$", "m1"),
            ("333$$$", "m1"),
            ("$$你", "m1"),
        ],
    ),
    (
        "heteronym",
        "advanced",
        "同音異讀",
        "<code translate=\"no\">{左碼}/{右碼}</code> 搵同一個寫法、至少兩個唔同讀音；某個聲調位唔限可以用 <code translate=\"no\">?</code>。只喺 0243 搜尋三檔用。",
        "Heteronym (variant readings)",
        "<code translate=\"no\">{leftCode}/{rightCode}</code> finds the same spelling with at least two readings; use <code translate=\"no\">?</code> where a tone digit can be anything. 0243 search tiers only.",
        [("33/34", "m1"), ("?3/?4", "m1"), ("3/4", "m1")],
    ),
    (
        "connective",
        "advanced",
        "連接詞複合詞",
        "三個字、中間係連接詞（與、和、或…）；<code translate=\"no\">~與~</code> 近義、<code translate=\"no\">!與!</code> 反義。",
        "Connective compounds",
        "Three-character compounds with a connective in the middle (與, 和, 或…); <code translate=\"no\">~與~</code> near-synonym, <code translate=\"no\">!與!</code> antonym.",
        [("!與!", "m1"), ("~與~", "m1")],
    ),
]


def js_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def label_for(q: str, mode: str) -> str:
    r = explain_query(q, mode)
    if not r.summary:
        raise SystemExit(f"no summary for {q!r} mode={mode}")
    return r.summary


def main() -> None:
    parts = ["const SECTIONS = ["]
    for sid, group, zt, zi, et, ei, exs in SECTIONS_SPEC:
        zh_ex = []
        en_ex = []
        ex_lines = []
        for q, mode in exs:
            lab = label_for(q, mode)
            zh_ex.append(f"        {{ label: {js_str(lab)} }},")
            en_ex.append(f"        {{ label: {js_str(lab)} }},")
            ex_lines.append(f"      {{ query: {js_str(q)}, mode: {js_str(mode)} }},")
        parts.append(
            f"""  {{
    id: {js_str(sid)},
    group: {js_str(group)},
    zh: {{
      title: {js_str(zt)},
      intro:
        {js_str(zi)},
      examples: [
{chr(10).join(zh_ex)}
      ],
    }},
    en: {{
      title: {js_str(et)},
      intro:
        {js_str(ei)},
      examples: [
{chr(10).join(en_ex)}
      ],
    }},
    examples: [
{chr(10).join(ex_lines)}
    ],
  }},"""
        )
    parts.append("];")
    blob = "\n".join(parts) + "\n"

    path = REPO / "shared" / "guide-i18n.mjs"
    text = path.read_text(encoding="utf-8")
    m = re.match(r"(?s)const SECTIONS = \[.*?\n\];\n", text)
    if not m:
        raise SystemExit("SECTIONS block not found")
    rest = text[m.end() :]
    rest = rest.replace(
        "每張卡嘅例子都可以撳一下直接搜尋。",
        "每章嘅例子都可以撳一下直接搜尋；說明字同搜尋欄下嘅語法解釋一樣。",
    )
    rest = rest.replace("更細嘅組合見各卡說明。", "更細嘅組合見各章說明。")
    rest = rest.replace(
        "See each card for finer patterns.",
        "See each chapter for finer patterns.",
    )
    path.write_text(blob + rest, encoding="utf-8", newline="\n")
    print("sections", len(SECTIONS_SPEC), "examples", sum(len(s[-1]) for s in SECTIONS_SPEC))


if __name__ == "__main__":
    main()
