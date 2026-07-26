const SECTIONS = [
  {
    id: "basic",
    group: "common",
zh: {
      title: "基本查詢",
      intro:
        "漢字、詞語、394052 碼或粵拼。",
      examples: [
        { label: "查詢詞條「香港」" },
        { label: "粵拼查詢「nei hou」（不需聲調）" },
        { label: "粵拼查詢「ming4 baak6」（有聲調）" },
      ],
    },
    zhHans: {
      title: "基本查询",
      intro:
        "汉字、词语、394052 码或粤拼。",
      examples: [
        { label: "查询词条「香港」" },
        { label: "粤拼查询「nei hou」（不需声调）" },
        { label: "粤拼查询「ming4 baak6」（有声调）" },
      ],
    },
    en: {
      title: "Basic lookup",
      intro:
        "Chinese characters, words, 394052 codes, or Jyutping.",
      examples: [
        { label: "查詢詞條「香港」" },
        { label: "粵拼查詢「nei hou」（不需聲調）" },
        { label: "粵拼查詢「ming4 baak6」（有聲調）" },
      ],
    },
    examples: [
      { query: "香港", mode: "m1" },
      { query: "nei hou", mode: "m1" },
      { query: "ming4 baak6", mode: "m1" },
    ],
  },
  {
    id: "digit",
    group: "common",
zh: {
      title: "0243 / 02493 / 394052 數字",
      intro:
        "純數字搵同碼詞條；02493 分清二聲；394052 六聲碼三／五聲分明。",
      examples: [
        { label: "查同23同音嘅字" },
        { label: "查同93同音嘅字" },
        { label: "查同45同音嘅字" },
      ],
    },
    zhHans: {
      title: "0243 / 02493 / 394052 数字",
      intro:
        "纯数字揾同码词条；02493 分清二声；394052 六声码三／五声分明。",
      examples: [
        { label: "查同23同音嘅字" },
        { label: "查同93同音嘅字" },
        { label: "查同45同音嘅字" },
      ],
    },
    en: {
      title: "0243 / 02493 / 394052 digits",
      intro:
        "Digits only: find entries sharing the code; 02493 separates the second tone; 394052 6-tone codes keep tones 3 and 5 distinct.",
      examples: [
        { label: "查同23同音嘅字" },
        { label: "查同93同音嘅字" },
        { label: "查同45同音嘅字" },
      ],
    },
    examples: [
      { query: "23", mode: "m1" },
      { query: "93", mode: "m2" },
      { query: "45", mode: "m3" },
    ],
  },
  {
    id: "equals",
    group: "common",
zh: {
      title: "同韻／同聲（=／^）",
      intro:
        "字後面加 <code translate=\"no\">=</code> → 同韻；字前面加 <code translate=\"no\">^</code> → 同聲。可整詞用，亦可數字夾住一個字同時規定聲調。參考字唔一定出現喺結果。",
      examples: [
        { label: "一個字：第 1 個字同「香」同韻" },
        { label: "兩個字：第 1 個字同「香」同韻，第 2 個字任意字" },
        { label: "一個字：第 1 個字同「香」同聲" },
        { label: "整詞同「香港」同韻（雙押）" },
        { label: "整詞同「香港」同聲（雙押）" },
        { label: "數字夾字「2我=3」：第 1 個字同 2 同音且同「我」同韻，第 2 個字同 3 同音" },
        { label: "數字夾字「2^我3」：第 1 個字同 2 同音且同「我」同聲，第 2 個字同 3 同音" },
        { label: "兩個字：第 1 個字任意字，第 2 個字同「香」同韻" },
        { label: "兼容原本舊語法：字前加 = 同聲（等同 ^香）" },
      ],
    },
    zhHans: {
      title: "同韵／同声（=／^）",
      intro:
        "字后面加 <code translate=\"no\">=</code> → 同韵；字前面加 <code translate=\"no\">^</code> → 同声。可整词用，亦可数字夹住一个字同时规定声调。参考字唔一定出现喺结果。",
      examples: [
        { label: "一个字：第 1 个字同「香」同韵" },
        { label: "两个字：第 1 个字同「香」同韵，第 2 个字任意字" },
        { label: "一个字：第 1 个字同「香」同声" },
        { label: "整词同「香港」同韵（双押）" },
        { label: "整词同「香港」同声（双押）" },
        { label: "数字夹字「2我=3」：第 1 个字同 2 同音且同「我」同韵，第 2 个字同 3 同音" },
        { label: "数字夹字「2^我3」：第 1 个字同 2 同音且同「我」同声，第 2 个字同 3 同音" },
        { label: "两个字：第 1 个字任意字，第 2 个字同「香」同韵" },
        { label: "兼容原本旧语法：字前加 = 同声（等同 ^香）" },
      ],
    },
    en: {
      title: "Same rhyme / initial (= / ^)",
      intro:
        "Put <code translate=\"no\">=</code> after a character for rhyme; put <code translate=\"no\">^</code> before it for initial. Works on a whole word, or with tone digits around one character. The reference character need not appear in results.",
      examples: [
        { label: "一個字：第 1 個字同「香」同韻" },
        { label: "兩個字：第 1 個字同「香」同韻，第 2 個字任意字" },
        { label: "一個字：第 1 個字同「香」同聲" },
        { label: "整詞同「香港」同韻（雙押）" },
        { label: "整詞同「香港」同聲（雙押）" },
        { label: "數字夾字「2我=3」：第 1 個字同 2 同音且同「我」同韻，第 2 個字同 3 同音" },
        { label: "數字夾字「2^我3」：第 1 個字同 2 同音且同「我」同聲，第 2 個字同 3 同音" },
        { label: "兩個字：第 1 個字任意字，第 2 個字同「香」同韻" },
        { label: "兼容原本舊語法：字前加 = 同聲（等同 ^香）" },
      ],
    },
    examples: [
      { query: "香=", mode: "m1" },
      { query: "香=?", mode: "m1" },
      { query: "^香", mode: "m1" },
      { query: "香港=", mode: "m1" },
      { query: "^香港", mode: "m1" },
      { query: "2我=3", mode: "m1" },
      { query: "2^我3", mode: "m1" },
      { query: "?香=", mode: "m1" },
      { query: "=香", mode: "m1" },
    ],
  },
  {
    id: "mask",
    group: "common",
zh: {
      title: "有啲字限定、有啲留空",
      intro:
        "定實你要嘅漢字或聲調數字；唔知嘅位用 <code translate=\"no\">?</code>／<code translate=\"no\">_</code>／<code translate=\"no\">%</code>（三個一樣）。開頭嘅 <code translate=\"no\">+</code> 可以唔打；通配 <code translate=\"no\">?</code> 後面亦唔使再加 <code translate=\"no\">+</code>（例如 <code translate=\"no\">?你?</code>）。",
      examples: [
        { label: "三個字：第 1 個字為「香」，第 2 個字任意字，第 3 個字任意字" },
        { label: "三個字：第 1 個字任意字，第 2 個字為「你」，第 3 個字任意字" },
        { label: "三個字：第 1 個字任意字，第 2 個字為「識」，第 3 個字任意字" },
        { label: "兩個字：第 1 個字同 3 同音，第 2 個字任意字" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字任意字" },
        { label: "兩個字：第 1 個字為「門」，第 2 個字同 0 同音" },
      ],
    },
    zhHans: {
      title: "有啲字限定、有啲留空",
      intro:
        "定实你要嘅汉字或声调数字；唔知嘅位用 <code translate=\"no\">?</code>／<code translate=\"no\">_</code>／<code translate=\"no\">%</code>（三个一样）。开头嘅 <code translate=\"no\">+</code> 可以唔打；通配 <code translate=\"no\">?</code> 后面亦唔使再加 <code translate=\"no\">+</code>（例如 <code translate=\"no\">?你?</code>）。",
      examples: [
        { label: "三个字：第 1 个字为「香」，第 2 个字任意字，第 3 个字任意字" },
        { label: "三个字：第 1 个字任意字，第 2 个字为「你」，第 3 个字任意字" },
        { label: "三个字：第 1 个字任意字，第 2 个字为「识」，第 3 个字任意字" },
        { label: "两个字：第 1 个字同 3 同音，第 2 个字任意字" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同 3 同音，第 3 个字任意字" },
        { label: "两个字：第 1 个字为「门」，第 2 个字同 0 同音" },
      ],
    },
    en: {
      title: "Lock some characters, leave others open",
      intro:
        "Set the characters or tone digits you need; fill unknowns with <code translate=\"no\">?</code> / <code translate=\"no\">_</code> / <code translate=\"no\">%</code> (all the same). A leading <code translate=\"no\">+</code> is optional; after a <code translate=\"no\">?</code> you usually omit <code translate=\"no\">+</code> (e.g. <code translate=\"no\">?你?</code>).",
      examples: [
        { label: "三個字：第 1 個字為「香」，第 2 個字任意字，第 3 個字任意字" },
        { label: "三個字：第 1 個字任意字，第 2 個字為「你」，第 3 個字任意字" },
        { label: "三個字：第 1 個字任意字，第 2 個字為「識」，第 3 個字任意字" },
        { label: "兩個字：第 1 個字同 3 同音，第 2 個字任意字" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字任意字" },
        { label: "兩個字：第 1 個字為「門」，第 2 個字同 0 同音" },
      ],
    },
    examples: [
      { query: "+香??", mode: "m1" },
      { query: "?你?", mode: "m1" },
      { query: "_識_", mode: "m1" },
      { query: "3_", mode: "m1" },
      { query: "23?", mode: "m1" },
      { query: "門0", mode: "m1" },
    ],
  },
  {
    id: "plus",
    group: "common",
zh: {
      title: "用 + 加長或標明位置",
      intro:
        "用 <code translate=\"no\">+</code> 喺<strong>冇通配</strong>時加多一個字，或者標明邊個位置（例如 <code translate=\"no\">23+好=</code>、<code translate=\"no\">23+o</code>）。若前面已經有 <code translate=\"no\">?</code>，通常<strong>唔使</strong>再打 <code translate=\"no\">+</code>（<code translate=\"no\">?香=</code> 等同舊寫法 <code translate=\"no\">?+香=</code>）。<code translate=\"no\">字=</code>＝同韻；<code translate=\"no\">+^字</code>＝同聲（舊 <code translate=\"no\">+=字</code> 仍相容）；冇標記就係要呢個字本身。打 <code translate=\"no\">*</code> 等同 <code translate=\"no\">+</code>。",
      examples: [
        { label: "兩個字：第 1 個字同 2 同音，第 2 個字同 3 同音且限定為手" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字為「好」" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字同「好」同韻" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字同「好」同聲" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字為「好」，第 3 個字同 3 同音" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同「好」同韻，第 3 個字同 3 同音" },
        { label: "兩個字：第 1 個字為「門」，第 2 個字同 0 同音" },
        { label: "兩個字：第 1 個字同「門」同韻，第 2 個字同 0 同音" },
      ],
    },
    zhHans: {
      title: "用 + 加长或标明位置",
      intro:
        "用 <code translate=\"no\">+</code> 喺<strong>冇通配</strong>时加多一个字，或者标明边个位置（例如 <code translate=\"no\">23+好=</code>、<code translate=\"no\">23+o</code>）。若前面已经有 <code translate=\"no\">?</code>，通常<strong>唔使</strong>再打 <code translate=\"no\">+</code>（<code translate=\"no\">?香=</code> 等同旧写法 <code translate=\"no\">?+香=</code>）。<code translate=\"no\">字=</code>＝同韵；<code translate=\"no\">+^字</code>＝同声（旧 <code translate=\"no\">+=字</code> 仍相容）；冇标记就系要呢个字本身。打 <code translate=\"no\">*</code> 等同 <code translate=\"no\">+</code>。",
      examples: [
        { label: "两个字：第 1 个字同 2 同音，第 2 个字同 3 同音且限定为手" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同 3 同音，第 3 个字为「好」" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同 3 同音，第 3 个字同「好」同韵" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同 3 同音，第 3 个字同「好」同声" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字为「好」，第 3 个字同 3 同音" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同「好」同韵，第 3 个字同 3 同音" },
        { label: "两个字：第 1 个字为「门」，第 2 个字同 0 同音" },
        { label: "两个字：第 1 个字同「门」同韵，第 2 个字同 0 同音" },
      ],
    },
    en: {
      title: "Use + to lengthen or mark a position",
      intro:
        "Use <code translate=\"no\">+</code> when there is <strong>no</strong> wildcard, to add a character or mark a position (e.g. <code translate=\"no\">23+好=</code>, <code translate=\"no\">23+o</code>). After a leading <code translate=\"no\">?</code>, <code translate=\"no\">+</code> is usually optional (<code translate=\"no\">?香=</code> equals older <code translate=\"no\">?+香=</code>). <code translate=\"no\">char=</code> = same rhyme; <code translate=\"no\">+^char</code> = same initial (legacy <code translate=\"no\">+=char</code> still works); without a mark that exact character is required. <code translate=\"no\">*</code> works like <code translate=\"no\">+</code>.",
      examples: [
        { label: "兩個字：第 1 個字同 2 同音，第 2 個字同 3 同音且限定為手" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字為「好」" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字同「好」同韻" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字同「好」同聲" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字為「好」，第 3 個字同 3 同音" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同「好」同韻，第 3 個字同 3 同音" },
        { label: "兩個字：第 1 個字為「門」，第 2 個字同 0 同音" },
        { label: "兩個字：第 1 個字同「門」同韻，第 2 個字同 0 同音" },
      ],
    },
    examples: [
      { query: "23@手", mode: "m1" },
      { query: "23+好", mode: "m1" },
      { query: "23+好=", mode: "m1" },
      { query: "23+^好", mode: "m1" },
      { query: "2+好3", mode: "m1" },
      { query: "2+好=3", mode: "m1" },
      { query: "+門0", mode: "m1" },
      { query: "+門=0", mode: "m1" },
    ],
  },
  {
    id: "multi",
    group: "advanced",
zh: {
      title: "多重同韻／同聲",
      intro:
        "用數字規定聲調，用參考字規定同韻或同聲（韻用尾 <code translate=\"no\">=</code>，聲用前 <code translate=\"no\">^</code>）；可用 <code translate=\"no\">?</code> 留空某個字，或令第一個字任意、其餘跟某詞逐字同韻／同聲。",
      examples: [
        { label: "數字夾字「23香=」：第 1 個字同 2 同音，第 2 個字同 3 同音且同「香」同韻" },
        { label: "四個字：第 1 個字同 0 同音，第 2 個字同 4 同音且同「困」同韻，第 3 個字同 4 同音，第 4 個字同 9 同音且同「倒」同韻" },
        { label: "四個字：第 1 個字同 0 同音，第 2 個字同 4 同音且同「困」同聲，第 3 個字同 4 同音，第 4 個字同 9 同音且同「倒」同聲" },
        { label: "四個字：第 1 個字任意字，第 2 個字同 4 同音且同「困」同韻，第 3 個字同 4 同音且同「潦」同韻，第 4 個字同 9 同音且同「倒」同韻" },
        { label: "三個字：第 1 個字任意字，第 2 個字同 3 同音且同「人」同韻，第 3 個字任意字" },
        { label: "四個字：第 1 個字同「窮」同韻，第 2 個字任意字，第 3 個字同「潦」同韻，第 4 個字同「倒」同韻" },
        { label: "四個字：第 1 個字同「窮」同韻，第 2 個字同「困」同韻，第 3 個字任意字，第 4 個字同「倒」同韻" },
        { label: "四個字：第 1 個字同「窮」同聲，第 2 個字任意字，第 3 個字同「潦」同聲，第 4 個字同「倒」同聲" },
        { label: "四個字：第 1 個字同「窮」同聲，第 2 個字同「困」同聲，第 3 個字任意字，第 4 個字同「倒」同聲" },
        { label: "首個字任意；第 2、第 3 個字同「香港」同韻（雙押）" },
        { label: "首個字任意；第 2、第 3、第 4 個字同「困潦倒」同韻（三押）" },
        { label: "首個字任意；第 2、第 3、第 4 個字同「困潦倒」同聲（三押）" },
      ],
    },
    zhHans: {
      title: "多重同韵／同声",
      intro:
        "用数字规定声调，用参考字规定同韵或同声（韵用尾 <code translate=\"no\">=</code>，声用前 <code translate=\"no\">^</code>）；可用 <code translate=\"no\">?</code> 留空某个字，或令第一个字任意、其余跟某词逐字同韵／同声。",
      examples: [
        { label: "数字夹字「23香=」：第 1 个字同 2 同音，第 2 个字同 3 同音且同「香」同韵" },
        { label: "四个字：第 1 个字同 0 同音，第 2 个字同 4 同音且同「困」同韵，第 3 个字同 4 同音，第 4 个字同 9 同音且同「倒」同韵" },
        { label: "四个字：第 1 个字同 0 同音，第 2 个字同 4 同音且同「困」同声，第 3 个字同 4 同音，第 4 个字同 9 同音且同「倒」同声" },
        { label: "四个字：第 1 个字任意字，第 2 个字同 4 同音且同「困」同韵，第 3 个字同 4 同音且同「潦」同韵，第 4 个字同 9 同音且同「倒」同韵" },
        { label: "三个字：第 1 个字任意字，第 2 个字同 3 同音且同「人」同韵，第 3 个字任意字" },
        { label: "四个字：第 1 个字同「穷」同韵，第 2 个字任意字，第 3 个字同「潦」同韵，第 4 个字同「倒」同韵" },
        { label: "四个字：第 1 个字同「穷」同韵，第 2 个字同「困」同韵，第 3 个字任意字，第 4 个字同「倒」同韵" },
        { label: "四个字：第 1 个字同「穷」同声，第 2 个字任意字，第 3 个字同「潦」同声，第 4 个字同「倒」同声" },
        { label: "四个字：第 1 个字同「穷」同声，第 2 个字同「困」同声，第 3 个字任意字，第 4 个字同「倒」同声" },
        { label: "首个字任意；第 2、第 3 个字同「香港」同韵（双押）" },
        { label: "首个字任意；第 2、第 3、第 4 个字同「困潦倒」同韵（三押）" },
        { label: "首个字任意；第 2、第 3、第 4 个字同「困潦倒」同声（三押）" },
      ],
    },
    en: {
      title: "Multi-slot rhyme / initial",
      intro:
        "Use digits for tone codes and reference characters for rhyme (trailing <code translate=\"no\">=</code>) or initial (leading <code translate=\"no\">^</code>); leave a slot open with <code translate=\"no\">?</code>, or free the first character while the rest follow a sample word.",
      examples: [
        { label: "數字夾字「23香=」：第 1 個字同 2 同音，第 2 個字同 3 同音且同「香」同韻" },
        { label: "四個字：第 1 個字同 0 同音，第 2 個字同 4 同音且同「困」同韻，第 3 個字同 4 同音，第 4 個字同 9 同音且同「倒」同韻" },
        { label: "四個字：第 1 個字同 0 同音，第 2 個字同 4 同音且同「困」同聲，第 3 個字同 4 同音，第 4 個字同 9 同音且同「倒」同聲" },
        { label: "四個字：第 1 個字任意字，第 2 個字同 4 同音且同「困」同韻，第 3 個字同 4 同音且同「潦」同韻，第 4 個字同 9 同音且同「倒」同韻" },
        { label: "三個字：第 1 個字任意字，第 2 個字同 3 同音且同「人」同韻，第 3 個字任意字" },
        { label: "四個字：第 1 個字同「窮」同韻，第 2 個字任意字，第 3 個字同「潦」同韻，第 4 個字同「倒」同韻" },
        { label: "四個字：第 1 個字同「窮」同韻，第 2 個字同「困」同韻，第 3 個字任意字，第 4 個字同「倒」同韻" },
        { label: "四個字：第 1 個字同「窮」同聲，第 2 個字任意字，第 3 個字同「潦」同聲，第 4 個字同「倒」同聲" },
        { label: "四個字：第 1 個字同「窮」同聲，第 2 個字同「困」同聲，第 3 個字任意字，第 4 個字同「倒」同聲" },
        { label: "首個字任意；第 2、第 3 個字同「香港」同韻（雙押）" },
        { label: "首個字任意；第 2、第 3、第 4 個字同「困潦倒」同韻（三押）" },
        { label: "首個字任意；第 2、第 3、第 4 個字同「困潦倒」同聲（三押）" },
      ],
    },
    examples: [
      { query: "23香=", mode: "m1" },
      { query: "04困=49倒=", mode: "m1" },
      { query: "04^困49^倒", mode: "m1" },
      { query: "?4困=4潦=9倒=", mode: "m1" },
      { query: "?3人=?", mode: "m1" },
      { query: "窮?潦倒=", mode: "m1" },
      { query: "窮困?倒=", mode: "m1" },
      { query: "^窮?潦倒", mode: "m1" },
      { query: "^窮困?倒", mode: "m1" },
      { query: "?香港=", mode: "m1" },
      { query: "?困潦倒=", mode: "m1" },
      { query: "?^困潦倒", mode: "m1" },
    ],
  },
  {
    id: "wildcard-code",
    group: "advanced",
zh: {
      title: "任意字＋數字碼＋尾字同韻",
      intro:
        "開頭用 <code translate=\"no\">?</code> 表示第一個字隨便，再打聲調數字；最後一個漢字決定尾字要同邊個同韻。碼同參考字之間若要再隔一格，先用 <code translate=\"no\">+</code>（如 <code translate=\"no\">?30+人</code>）。",
      examples: [
        { label: "三個字：第 1 個字任意字，第 2 個字同 3 同音，第 3 個字同 0 同音且同「人」同韻" },
        { label: "四個字：第 1 個字任意字，第 2 個字同 3 同音，第 3 個字同 0 同音，第 4 個字同「人」同韻" },
      ],
    },
    zhHans: {
      title: "任意字＋数字码＋尾字同韵",
      intro:
        "开头用 <code translate=\"no\">?</code> 表示第一个字随便，再打声调数字；最后一个汉字决定尾字要同边个同韵。码同参考字之间若要再隔一格，先用 <code translate=\"no\">+</code>（如 <code translate=\"no\">?30+人</code>）。",
      examples: [
        { label: "三个字：第 1 个字任意字，第 2 个字同 3 同音，第 3 个字同 0 同音且同「人」同韵" },
        { label: "四个字：第 1 个字任意字，第 2 个字同 3 同音，第 3 个字同 0 同音，第 4 个字同「人」同韵" },
      ],
    },
    en: {
      title: "Any char + tone digits + last rhymes",
      intro:
        "Leading <code translate=\"no\">?</code> leaves the first character open, then tone digits; the last character sets the rhyme for the end. Use <code translate=\"no\">+</code> between digits and the reference when you need an extra slot (e.g. <code translate=\"no\">?30+人</code>).",
      examples: [
        { label: "三個字：第 1 個字任意字，第 2 個字同 3 同音，第 3 個字同 0 同音且同「人」同韻" },
        { label: "四個字：第 1 個字任意字，第 2 個字同 3 同音，第 3 個字同 0 同音，第 4 個字同「人」同韻" },
      ],
    },
    examples: [
      { query: "?30人", mode: "m1" },
      { query: "?30+人", mode: "m1" },
    ],
  },
  {
    id: "jyutping-anchor",
    group: "advanced",
zh: {
      title: "用粵拼指定某個字",
      intro:
        "唔想打漢字參考字時，可以用粵拼字母標明某個字嘅韻母、完整音節或聲母。通配後面通常唔使 <code translate=\"no\">+</code>（如 <code translate=\"no\">?hon</code>、<code translate=\"no\">?m?</code>）；數字貼粵拼、或者要加長詞長時先要用 <code translate=\"no\">+</code>（如 <code translate=\"no\">3+ngo4</code>、<code translate=\"no\">23+o</code> 唔等同 <code translate=\"no\">23o</code>）。",
      examples: [
        { label: "兩個字：第 1 個字任意字，第 2 個字粵拼音節 hon" },
        { label: "三個字：第 1 個字任意字，第 2 個字同韻母 yut，第 3 個字任意字" },
        { label: "三個字：第 1 個字任意字，第 2 個字粵拼音節 syut，第 3 個字任意字" },
        { label: "三個字：第 1 個字同 3 同音，第 2 個字粵拼音節 ngo，第 3 個字同 4 同音" },
        { label: "兩個字：第 1 個字粵拼音節 hon，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字粵拼音節 hon，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字同聲母 h，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字同聲母 gw，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字同 2 同音，第 2 個字同韻母 o" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字同韻母 o" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同韻母 ei，第 3 個字同 0 同音" },
        { label: "三個字：第 1 個字任意字，第 2 個字同韻母 ng，第 3 個字任意字" },
        { label: "兩個字：第 1 個字同韻母 ng，第 2 個字同 4 同音" },
      ],
    },
    zhHans: {
      title: "用粤拼指定某个字",
      intro:
        "唔想打汉字参考字时，可以用粤拼字母标明某个字嘅韵母、完整音节或声母。通配后面通常唔使 <code translate=\"no\">+</code>（如 <code translate=\"no\">?hon</code>、<code translate=\"no\">?m?</code>）；数字贴粤拼、或者要加长词长时先要用 <code translate=\"no\">+</code>（如 <code translate=\"no\">3+ngo4</code>、<code translate=\"no\">23+o</code> 唔等同 <code translate=\"no\">23o</code>）。",
      examples: [
        { label: "两个字：第 1 个字任意字，第 2 个字粤拼音节 hon" },
        { label: "三个字：第 1 个字任意字，第 2 个字同韵母 yut，第 3 个字任意字" },
        { label: "三个字：第 1 个字任意字，第 2 个字粤拼音节 syut，第 3 个字任意字" },
        { label: "三个字：第 1 个字同 3 同音，第 2 个字粤拼音节 ngo，第 3 个字同 4 同音" },
        { label: "两个字：第 1 个字粤拼音节 hon，第 2 个字同 4 同音" },
        { label: "两个字：第 1 个字粤拼音节 hon，第 2 个字同 4 同音" },
        { label: "两个字：第 1 个字同声母 h，第 2 个字同 4 同音" },
        { label: "两个字：第 1 个字同声母 gw，第 2 个字同 4 同音" },
        { label: "两个字：第 1 个字同 2 同音，第 2 个字同韵母 o" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同 3 同音，第 3 个字同韵母 o" },
        { label: "三个字：第 1 个字同 2 同音，第 2 个字同韵母 ei，第 3 个字同 0 同音" },
        { label: "三个字：第 1 个字任意字，第 2 个字同韵母 ng，第 3 个字任意字" },
        { label: "两个字：第 1 个字同韵母 ng，第 2 个字同 4 同音" },
      ],
    },
    en: {
      title: "Specify a syllable with Jyutping",
      intro:
        "Instead of a Chinese reference character, type Jyutping letters for a final, full syllable, or initial. After <code translate=\"no\">?</code>, <code translate=\"no\">+</code> is usually optional (e.g. <code translate=\"no\">?hon</code>, <code translate=\"no\">?m?</code>); use <code translate=\"no\">+</code> when digits abut Jyutping or you need a longer word (<code translate=\"no\">3+ngo4</code>; <code translate=\"no\">23+o</code> ≠ <code translate=\"no\">23o</code>).",
      examples: [
        { label: "兩個字：第 1 個字任意字，第 2 個字粵拼音節 hon" },
        { label: "三個字：第 1 個字任意字，第 2 個字同韻母 yut，第 3 個字任意字" },
        { label: "三個字：第 1 個字任意字，第 2 個字粵拼音節 syut，第 3 個字任意字" },
        { label: "三個字：第 1 個字同 3 同音，第 2 個字粵拼音節 ngo，第 3 個字同 4 同音" },
        { label: "兩個字：第 1 個字粵拼音節 hon，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字粵拼音節 hon，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字同聲母 h，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字同聲母 gw，第 2 個字同 4 同音" },
        { label: "兩個字：第 1 個字同 2 同音，第 2 個字同韻母 o" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同 3 同音，第 3 個字同韻母 o" },
        { label: "三個字：第 1 個字同 2 同音，第 2 個字同韻母 ei，第 3 個字同 0 同音" },
        { label: "三個字：第 1 個字任意字，第 2 個字同韻母 ng，第 3 個字任意字" },
        { label: "兩個字：第 1 個字同韻母 ng，第 2 個字同 4 同音" },
      ],
    },
    examples: [
      { query: "?hon", mode: "m1" },
      { query: "?+yut?", mode: "m1" },
      { query: "?+syut?", mode: "m1" },
      { query: "3+ngo4", mode: "m1" },
      { query: "3hon4", mode: "m1" },
      { query: "3$漢4", mode: "m1" },
      { query: "3h4", mode: "m1" },
      { query: "3gw4", mode: "m1" },
      { query: "23o", mode: "m1" },
      { query: "23+o", mode: "m1" },
      { query: "23ei0", mode: "m1" },
      { query: "?m?", mode: "m1" },
      { query: "3m4", mode: "m1" },
    ],
  },
  {
    id: "ping-ze",
    group: "advanced",
zh: {
      title: "平仄（平／仄）",
      intro:
        "<code translate=\"no\">P</code>＝平、<code translate=\"no\">Z</code>＝仄；數字＝嗰個字要同呢個聲調同音。平仄模式下可喺搜尋欄下切換 <strong>0243</strong>／<strong>02493</strong>／<strong>394052</strong>；P／Z 一律按六聲判定。",
      examples: [
        { label: "查平、仄嘅兩個字詞" },
        { label: "查平、仄、與 3 同音嘅三個字詞" },
        { label: "查平、仄嘅兩個字詞" },
        { label: "查與 ^ 同音、與 好 同音、平、仄嘅四個字詞" },
      ],
    },
    zhHans: {
      title: "平仄（平／仄）",
      intro:
        "<code translate=\"no\">P</code>＝平、<code translate=\"no\">Z</code>＝仄；数字＝𠮶个字要同呢个声调同音。平仄模式下可喺搜寻栏下切换 <strong>0243</strong>／<strong>02493</strong>／<strong>394052</strong>；P／Z 一律按六声判定。",
      examples: [
        { label: "查平、仄嘅两个字词" },
        { label: "查平、仄、与 3 同音嘅三个字词" },
        { label: "查平、仄嘅两个字词" },
        { label: "查与 ^ 同音、与 好 同音、平、仄嘅四个字词" },
      ],
    },
    en: {
      title: "Ping / ze pattern",
      intro:
        "<code translate=\"no\">P</code> = ping, <code translate=\"no\">Z</code> = ze; a digit means that character must match that tone. In ping–ze mode, pick <strong>0243</strong> / <strong>02493</strong> / <strong>394052</strong> under the search box; P/Z always use the 6-tone scale.",
      examples: [
        { label: "查平、仄嘅兩個字詞" },
        { label: "查平、仄、與 3 同音嘅三個字詞" },
        { label: "查平、仄嘅兩個字詞" },
        { label: "查與 ^ 同音、與 好 同音、平、仄嘅四個字詞" },
      ],
    },
    examples: [
      { query: "PZ", mode: "pz" },
      { query: "PZ3", mode: "pz" },
      { query: "PZ好=", mode: "pz" },
      { query: "=好PZ", mode: "pz" },
    ],
  },
  {
    id: "relation",
    group: "advanced",
zh: {
      title: "近義 / 反義",
      intro:
        "<code translate=\"no\">~</code> 近義、<code translate=\"no\">!</code> 反義；可加碼前綴。僅 0243搜尋三檔（唔包括近反義模式）。",
      examples: [
        { label: "查「開心」嘅近義詞" },
        { label: "查「苦悶」嘅反義詞" },
        { label: "查「開心」嘅碼 33 反義詞" },
      ],
    },
    zhHans: {
      title: "近义 / 反义",
      intro:
        "<code translate=\"no\">~</code> 近义、<code translate=\"no\">!</code> 反义；可加码前缀。仅 0243搜寻三档（唔包括近反义模式）。",
      examples: [
        { label: "查「开心」嘅近义词" },
        { label: "查「苦闷」嘅反义词" },
        { label: "查「开心」嘅码 33 反义词" },
      ],
    },
    en: {
      title: "Synonym / antonym",
      intro:
        "<code translate=\"no\">~</code> near-synonym, <code translate=\"no\">!</code> antonym; optional code prefix. 0243 search tiers only (not synonym/antonym mode).",
      examples: [
        { label: "查「開心」嘅近義詞" },
        { label: "查「苦悶」嘅反義詞" },
        { label: "查「開心」嘅碼 33 反義詞" },
      ],
    },
    examples: [
      { query: "~開心", mode: "m1" },
      { query: "!苦悶", mode: "m1" },
      { query: "33!開心", mode: "m1" },
    ],
  },
  {
    id: "syn-pool",
    group: "advanced",
zh: {
      title: "近反義模式（瀏覽相關詞）",
      intro:
        "切換近反義模式，打一個詞就列出近義、反義同相關詞。",
      examples: [
        { label: "查詢詞條「開心」" },
      ],
    },
    zhHans: {
      title: "近反义模式（浏览相关词）",
      intro:
        "切换近反义模式，打一个词就列出近义、反义同相关词。",
      examples: [
        { label: "查询词条「开心」" },
      ],
    },
    en: {
      title: "Synonym/antonym mode (browse related words)",
      intro:
        "Switch to synonym/antonym mode and type a word to list near-synonyms, antonyms, and related words.",
      examples: [
        { label: "查詢詞條「開心」" },
      ],
    },
    examples: [
      { query: "開心", mode: "syn" },
    ],
  },
  {
    id: "compound-syn",
    group: "advanced",
zh: {
      title: "近義複合詞",
      intro:
        "<code translate=\"no\">~~</code> 搵二字近義複合；可加碼前綴或尾韻字。",
      examples: [
        { label: "查詢近義複合詞" },
        { label: "查詢近義複合詞" },
        { label: "查詢近義複合詞" },
        { label: "查詢近義複合詞" },
      ],
    },
    zhHans: {
      title: "近义复合词",
      intro:
        "<code translate=\"no\">~~</code> 揾二字近义复合；可加码前缀或尾韵字。",
      examples: [
        { label: "查询近义复合词" },
        { label: "查询近义复合词" },
        { label: "查询近义复合词" },
        { label: "查询近义复合词" },
      ],
    },
    en: {
      title: "Near-synonym compounds",
      intro:
        "<code translate=\"no\">~~</code> finds two-character near-synonym compounds; optional code prefix or trailing rhyme character.",
      examples: [
        { label: "查詢近義複合詞" },
        { label: "查詢近義複合詞" },
        { label: "查詢近義複合詞" },
        { label: "查詢近義複合詞" },
      ],
    },
    examples: [
      { query: "~~", mode: "m1" },
      { query: "33~~", mode: "m1" },
      { query: "~~你", mode: "m1" },
      { query: "33~~你", mode: "m1" },
    ],
  },
  {
    id: "compound-ant",
    group: "advanced",
zh: {
      title: "反義複合詞",
      intro:
        "<code translate=\"no\">!!</code> 搵二字反義複合；可加碼前綴或尾韻字。",
      examples: [
        { label: "查詢反義複合詞" },
        { label: "查詢反義複合詞" },
        { label: "查詢反義複合詞" },
        { label: "查詢反義複合詞" },
      ],
    },
    zhHans: {
      title: "反义复合词",
      intro:
        "<code translate=\"no\">!!</code> 揾二字反义复合；可加码前缀或尾韵字。",
      examples: [
        { label: "查询反义复合词" },
        { label: "查询反义复合词" },
        { label: "查询反义复合词" },
        { label: "查询反义复合词" },
      ],
    },
    en: {
      title: "Antonym compounds",
      intro:
        "<code translate=\"no\">!!</code> finds two-character antonym compounds; optional code prefix or trailing rhyme character.",
      examples: [
        { label: "查詢反義複合詞" },
        { label: "查詢反義複合詞" },
        { label: "查詢反義複合詞" },
        { label: "查詢反義複合詞" },
      ],
    },
    examples: [
      { query: "!!", mode: "m1" },
      { query: "33!!", mode: "m1" },
      { query: "!!你", mode: "m1" },
      { query: "33!!你", mode: "m1" },
    ],
  },
  {
    id: "doubled",
    group: "advanced",
zh: {
      title: "雙聲疊韻字",
      intro:
        "連續 <code translate=\"no\">$</code> 的個數 = 詞長（2–4）；各字音節相同（聲調不限）；可加碼前綴或尾韻字。語法鏡像 <code translate=\"no\">~~</code>。",
      examples: [
        { label: "查2字雙聲疊韻字（各字音節相同，聲調不限）" },
        { label: "查3字雙聲疊韻字（各字音節相同，聲調不限）" },
        { label: "查4字雙聲疊韻字（各字音節相同，聲調不限）" },
        { label: "查2字雙聲疊韻字（碼 33）" },
        { label: "查3字雙聲疊韻字（碼 333）" },
        { label: "查2字雙聲疊韻字（尾字同「你」同韻）" },
      ],
    },
    zhHans: {
      title: "双声叠韵字",
      intro:
        "连续 <code translate=\"no\">$</code> 的个数 = 词长（2–4）；各字音节相同（声调不限）；可加码前缀或尾韵字。语法镜像 <code translate=\"no\">~~</code>。",
      examples: [
        { label: "查2字双声叠韵字（各字音节相同，声调不限）" },
        { label: "查3字双声叠韵字（各字音节相同，声调不限）" },
        { label: "查4字双声叠韵字（各字音节相同，声调不限）" },
        { label: "查2字双声叠韵字（码 33）" },
        { label: "查3字双声叠韵字（码 333）" },
        { label: "查2字双声叠韵字（尾字同「你」同韵）" },
      ],
    },
    en: {
      title: "Reduplicated same-syllable words",
      intro:
        "Count of consecutive <code translate=\"no\">$</code> = word length (2–4); each character shares the same syllable (any tone); optional code prefix or trailing rhyme char. Syntax mirrors <code translate=\"no\">~~</code>.",
      examples: [
        { label: "查2字雙聲疊韻字（各字音節相同，聲調不限）" },
        { label: "查3字雙聲疊韻字（各字音節相同，聲調不限）" },
        { label: "查4字雙聲疊韻字（各字音節相同，聲調不限）" },
        { label: "查2字雙聲疊韻字（碼 33）" },
        { label: "查3字雙聲疊韻字（碼 333）" },
        { label: "查2字雙聲疊韻字（尾字同「你」同韻）" },
      ],
    },
    examples: [
      { query: "$$", mode: "m1" },
      { query: "$$$", mode: "m1" },
      { query: "$$$$", mode: "m1" },
      { query: "33$$", mode: "m1" },
      { query: "333$$$", mode: "m1" },
      { query: "$$你", mode: "m1" },
    ],
  },
  {
    id: "heteronym",
    group: "advanced",
zh: {
      title: "同音異讀",
      intro:
        "<code translate=\"no\">{左碼}/{右碼}</code> 搵同一個寫法、至少兩個唔同讀音；某個聲調位唔限可以用 <code translate=\"no\">?</code>。只喺 0243 搜尋三檔用。",
      examples: [
        { label: "查同字面異讀（33/34）：搵至少兩個唔同讀音，分別符合左右碼位模板" },
        { label: "查同字面異讀（?3/?4）：搵至少兩個唔同讀音，分別符合左右碼位模板" },
        { label: "查同字面異讀（3/4）：搵至少兩個唔同讀音，分別符合左右碼位模板" },
      ],
    },
    zhHans: {
      title: "同音异读",
      intro:
        "<code translate=\"no\">{左码}/{右码}</code> 揾同一个写法、至少两个唔同读音；某个声调位唔限可以用 <code translate=\"no\">?</code>。只喺 0243 搜寻三档用。",
      examples: [
        { label: "查同字面异读（33/34）：揾至少两个唔同读音，分别符合左右码位模板" },
        { label: "查同字面异读（?3/?4）：揾至少两个唔同读音，分别符合左右码位模板" },
        { label: "查同字面异读（3/4）：揾至少两个唔同读音，分别符合左右码位模板" },
      ],
    },
    en: {
      title: "Heteronym (variant readings)",
      intro:
        "<code translate=\"no\">{leftCode}/{rightCode}</code> finds the same spelling with at least two readings; use <code translate=\"no\">?</code> where a tone digit can be anything. 0243 search tiers only.",
      examples: [
        { label: "查同字面異讀（33/34）：搵至少兩個唔同讀音，分別符合左右碼位模板" },
        { label: "查同字面異讀（?3/?4）：搵至少兩個唔同讀音，分別符合左右碼位模板" },
        { label: "查同字面異讀（3/4）：搵至少兩個唔同讀音，分別符合左右碼位模板" },
      ],
    },
    examples: [
      { query: "33/34", mode: "m1" },
      { query: "?3/?4", mode: "m1" },
      { query: "3/4", mode: "m1" },
    ],
  },
  {
    id: "connective",
    group: "advanced",
zh: {
      title: "連接詞複合詞",
      intro:
        "三個字、中間係連接詞（與、和、或…）；<code translate=\"no\">~與~</code> 近義、<code translate=\"no\">!與!</code> 反義。",
      examples: [
        { label: "查詢含「與」嘅反義複合詞" },
        { label: "查詢含「與」嘅近義複合詞" },
      ],
    },
    zhHans: {
      title: "连接词复合词",
      intro:
        "三个字、中间系连接词（与、和、或…）；<code translate=\"no\">~与~</code> 近义、<code translate=\"no\">!与!</code> 反义。",
      examples: [
        { label: "查询含「与」嘅反义复合词" },
        { label: "查询含「与」嘅近义复合词" },
      ],
    },
    en: {
      title: "Connective compounds",
      intro:
        "Three-character compounds with a connective in the middle (與, 和, 或…); <code translate=\"no\">~與~</code> near-synonym, <code translate=\"no\">!與!</code> antonym.",
      examples: [
        { label: "查詢含「與」嘅反義複合詞" },
        { label: "查詢含「與」嘅近義複合詞" },
      ],
    },
    examples: [
      { query: "!與!", mode: "m1" },
      { query: "~與~", mode: "m1" },
    ],
  },
];
const GUIDE_HERO = {
  zh: {
    eyebrow: 'Search manual',
    title: '所有搜尋語法',
    lede:
      '每個例子都可以直接執行。點擊後會回到搜尋頁、套用建議模式，並送出查詢。<strong>口訣：</strong><code translate="no">=</code> 喺參考字<strong>後面</strong> → 同韻；<code translate="no">^</code> 喺參考字<strong>前面</strong> → 同聲（舊寫法字前 <code translate="no">=</code> 仍相容）。留空用 <code translate="no">?</code>；用 <code translate="no">+</code> 加長時，若前面已有 <code translate="no">?</code> 通常可省略。',
  },
  zhHans: {
    eyebrow: 'Search manual',
    title: '所有搜寻语法',
    lede:
      '每个例子都可以直接执行。点击后会回到搜寻页、套用建议模式，并送出查询。<strong>口诀：</strong><code translate="no">=</code> 喺参考字<strong>后面</strong> → 同韵；<code translate="no">^</code> 喺参考字<strong>前面</strong> → 同声（旧写法字前 <code translate="no">=</code> 仍相容）。留空用 <code translate="no">?</code>；用 <code translate="no">+</code> 加长时，若前面已有 <code translate="no">?</code> 通常可省略。',
  },
  en: {
    eyebrow: 'Search manual',
    title: 'All search syntax',
    lede:
      'Every example is clickable. Tap one to return to search, apply the suggested mode, and run the query. <strong>Mnemonic:</strong> <code translate="no">=</code> <strong>after</strong> the reference character → rhyme; <code translate="no">^</code> <strong>before</strong> it → initial (legacy leading <code translate="no">=</code> still works). Gaps use <code translate="no">?</code>; after a <code translate="no">?</code>, a following <code translate="no">+</code> is usually optional.',
  },
};

const GUIDE_INTRO = {
  zh: {
    title: '點樣睇呢頁',
    paragraphs: [
      '下面按<strong>常用</strong>同<strong>進階</strong>分組。每章嘅例子都可以撳一下直接搜尋；說明字同搜尋欄下嘅語法解釋一樣。',
      '<strong>口訣：</strong><code translate="no">=</code> 喺參考字<strong>後面</strong> → 同韻；<code translate="no">^</code> 喺參考字<strong>前面</strong> → 同聲（舊寫法字前 <code translate="no">=</code> 仍相容）。留空用 <code translate="no">?</code>／<code translate="no">_</code>／<code translate="no">%</code>；加長用 <code translate="no">+</code>（前面已有 <code translate="no">?</code> 時通常可省）。',
      '數字碼搵同音；近反義用 <code translate="no">~</code>／<code translate="no">!</code>（或切換近反義模式）。更細嘅組合見各章說明。',
    ],
  },
  zhHans: {
    title: '点样睇呢页',
    paragraphs: [
      '下面按<strong>常用</strong>同<strong>进阶</strong>分组。每章嘅例子都可以揿一下直接搜寻；说明字同搜寻栏下嘅语法解释一样。',
      '<strong>口诀：</strong><code translate="no">=</code> 喺参考字<strong>后面</strong> → 同韵；<code translate="no">^</code> 喺参考字<strong>前面</strong> → 同声（旧写法字前 <code translate="no">=</code> 仍相容）。留空用 <code translate="no">?</code>／<code translate="no">_</code>／<code translate="no">%</code>；加长用 <code translate="no">+</code>（前面已有 <code translate="no">?</code> 时通常可省）。',
      '数字码揾同音；近反义用 <code translate="no">~</code>／<code translate="no">!</code>（或切换近反义模式）。更细嘅组合见各章说明。',
    ],
  },
  en: {
    title: 'How to read this page',
    paragraphs: [
      'Cards are grouped into <strong>Common</strong> and <strong>Advanced</strong>. Every example is clickable and runs a search.',
      '<strong>Mnemonic:</strong> <code translate="no">=</code> <strong>after</strong> a reference character → rhyme; <code translate="no">^</code> <strong>before</strong> it → initial (legacy leading <code translate="no">=</code> still works). Gaps use <code translate="no">?</code> / <code translate="no">_</code> / <code translate="no">%</code>; lengthen with <code translate="no">+</code> (usually omit it right after <code translate="no">?</code>).',
      'Tone digits find same-tone words; synonyms/antonyms use <code translate="no">~</code> / <code translate="no">!</code> (or synonym mode). See each chapter for finer patterns.',
    ],
  },
};
function resolveLang(lang) {
  return lang === 'en' ? 'en' : lang === 'zh-Hans' ? 'zhHans' : 'zh';
}

function renderCardTitle(title) {
  return title
    .replace(/（\+）/g, '（<code translate="no">+</code>）')
    .replace(/（=／\^）/g, '（<code translate="no">=</code>／<code translate="no">^</code>）')
    .replace(/（=）/g, '（<code translate="no">=</code>）');
}

export function getGuideHero(lang) {
  return GUIDE_HERO[resolveLang(lang)];
}

export function getGuideIntro(lang) {
  return GUIDE_INTRO[resolveLang(lang)];
}

const GUIDE_GROUP_LABEL = {
  zh: { common: '常用', advanced: '進階' },
  zhHans: { common: '常用', advanced: '进阶' },
  en: { common: 'Common', advanced: 'Advanced' }
};

export function getGuideGroupLabel(group, lang) {
  const l = resolveLang(lang);
  return GUIDE_GROUP_LABEL[l][group] || group;
}

const GUIDE_TOC_COPY = {
  zh: { label: '目錄', open: '顯示目錄', close: '收起目錄' },
  zhHans: { label: '目录', open: '显示目录', close: '收起目录' },
  en: { label: 'Contents', open: 'Show contents', close: 'Hide contents' }
};

export function getGuideTocCopy(lang) {
  return GUIDE_TOC_COPY[resolveLang(lang)];
}

export function guideSectionDomId(id) {
  return `guide-sec-${id}`;
}

export function getGuideSections(lang) {
  const l = resolveLang(lang);
  return SECTIONS.map((section) => ({
    id: section.id,
    group: section.group || 'advanced',
    title: section[l].title,
    intro: section[l].intro,
    examples: section.examples.map((ex, i) => {
      const copy = section[l].examples[i];
      const item = {
        query: ex.query,
        mode: ex.mode,
        label: copy.label,
      };
      if (copy.title) item.title = copy.title;
      return item;
    }),
  }));
}

function renderGuideChaptersHtml(lang) {
  const l = resolveLang(lang);
  const parts = [];
  let lastGroup = null;
  for (const section of SECTIONS) {
    const group = section.group || 'advanced';
    if (group !== lastGroup) {
      parts.push(
        `<h2 class="guide-group-label">${getGuideGroupLabel(group, l)}</h2>`,
      );
      lastGroup = group;
    }
    const copy = section[l];
    const buttons = section.examples
      .map((ex, i) => {
        const exCopy = copy.examples[i];
        const titleAttr = exCopy.title ? ` title="${exCopy.title.replace(/"/g, '&quot;')}"` : '';
        return (
          `<button class="guide-example" type="button" data-query="${ex.query}" data-mode="${ex.mode}"${titleAttr}>` +
          `<code translate="no">${ex.query}</code>` +
          `<span>${exCopy.label}</span>` +
          `</button>`
        );
      })
      .join('\n            ');
    const secId = guideSectionDomId(section.id);
    parts.push(
      `<section class="guide-chapter" id="${secId}">` +
        `<h3>${renderCardTitle(copy.title)}</h3>` +
        `<p>${copy.intro}</p>` +
        `<div class="guide-examples">\n            ${buttons}\n          </div>` +
        `</section>`,
    );
  }
  return parts.join('\n\n        ');
}

function renderGuideTocHtml(lang) {
  const l = resolveLang(lang);
  const toc = getGuideTocCopy(l);
  const links = SECTIONS.map((section) => {
    const title = section[l].title.replace(/<[^>]+>/g, '');
    return (
      `<li><a class="guide-toc__link" href="#${guideSectionDomId(section.id)}">${title}</a></li>`
    );
  }).join('');
  return (
    `<nav class="guide-toc" aria-label="${toc.label}">` +
      `<button type="button" class="guide-toc__toggle" aria-expanded="false" aria-controls="guideTocPanel">` +
        `${toc.label}` +
      `</button>` +
      `<div class="guide-toc__panel" id="guideTocPanel">` +
        `<p class="guide-toc__title">${toc.label}</p>` +
        `<ol class="guide-toc__list">${links}</ol>` +
      `</div>` +
    `</nav>`
  );
}

/** @deprecated prefer renderGuideLayoutHtml; kept for seam checks */
export function renderGuideGridHtml(lang) {
  return renderGuideChaptersHtml(lang);
}

export function renderGuideLayoutHtml(lang) {
  return (
    `${renderGuideTocHtml(lang)}` +
    `<div class="guide-chapters" id="guideGrid">\n        ${renderGuideChaptersHtml(lang)}\n      </div>`
  );
}

/** Scroll-spy + mobile TOC toggle. Root must be the scrolling .guide-view. */
export function bindGuideNav(root) {
  if (!root) return () => {};
  const prev = root._guideNavCleanup;
  if (typeof prev === 'function') prev();

  const toc = root.querySelector('.guide-toc');
  const chapters = [...root.querySelectorAll('.guide-chapter[id]')];
  if (!toc || !chapters.length) return () => {};

  const toggle = toc.querySelector('.guide-toc__toggle');
  const links = [...toc.querySelectorAll('.guide-toc__link')];
  const byId = new Map(chapters.map((el) => [el.id, el]));

  const setOpen = (open) => {
    toc.classList.toggle('is-open', open);
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  const onToggle = () => setOpen(!toc.classList.contains('is-open'));
  toggle?.addEventListener('click', onToggle);

  const onLinkClick = (event) => {
    const href = event.currentTarget.getAttribute('href');
    if (!href?.startsWith('#')) return;
    const target = byId.get(href.slice(1));
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setOpen(false);
    links.forEach((a) => a.removeAttribute('aria-current'));
    event.currentTarget.setAttribute('aria-current', 'true');
  };
  links.forEach((a) => a.addEventListener('click', onLinkClick));

  let activeId = '';
  const setActive = (id) => {
    if (!id || id === activeId) return;
    activeId = id;
    links.forEach((a) => {
      const match = a.getAttribute('href') === `#${id}`;
      if (match) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  };

  let observer = null;
  if (typeof IntersectionObserver !== 'undefined') {
    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]?.target?.id) setActive(visible[0].target.id);
      },
      { root, rootMargin: '-12% 0px -55% 0px', threshold: [0, 0.15, 0.4] },
    );
    chapters.forEach((ch) => observer.observe(ch));
  }

  const cleanup = () => {
    toggle?.removeEventListener('click', onToggle);
    links.forEach((a) => a.removeEventListener('click', onLinkClick));
    observer?.disconnect();
    root._guideNavCleanup = null;
  };
  root._guideNavCleanup = cleanup;
  return cleanup;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

export function applyGuideLang(lang) {
  const l = resolveLang(lang);
  const hero = getGuideHero(l);
  const intro = getGuideIntro(l);
  setText('guideEyebrow', hero.eyebrow);
  setText('guideTitle', hero.title);
  setHtml('guideLede', hero.lede);
  setText('guideIntroTitle', intro.title);
  setHtml('guideIntroBody', intro.paragraphs.map((p) => `<p>${p}</p>`).join(''));
  const layout = document.getElementById('guideLayout');
  const guideView = document.getElementById('guideView');
  if (layout) {
    layout.innerHTML = renderGuideLayoutHtml(l);
    bindGuideNav(guideView);
    return;
  }
  const grid = document.getElementById('guideGrid');
  if (grid) grid.innerHTML = renderGuideChaptersHtml(l);
  bindGuideNav(guideView);
}
