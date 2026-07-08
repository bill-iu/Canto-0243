const SECTIONS = [
  {
    id: 'basic',
    zh: {
      title: '基本查詢',
      intro: '漢字、詞語、0243 碼或粵拼。',
      examples: [
        { label: '查呢個字嘅所有讀音' },
        { label: '查呢個詞語' },
        { label: '粵拼查詢（冇聲調）' },
        { label: '粵拼查詢（有聲調）' },
      ],
    },
    en: {
      title: 'Basic lookup',
      intro: 'Chinese characters, words, 0243 codes, or Jyutping.',
      examples: [
        { label: 'All readings for this character' },
        { label: 'Look up this word' },
        { label: 'Jyutping lookup (no tone numbers)' },
        { label: 'Jyutping lookup (with tone numbers)' },
      ],
    },
    examples: [
      { query: '就', mode: 'm1' },
      { query: '你好', mode: 'm1' },
      { query: 'nei hou', mode: 'm1' },
      { query: 'ming4 baak6', mode: 'm1' },
    ],
  },
  {
    id: 'digit',
    zh: {
      title: '0243 / 02493 數字',
      intro: '純數字搵同碼詞條；02493 分清二聲。',
      examples: [{ label: '找同音字' }, { label: '02493模式 分清二聲' }],
    },
    en: {
      title: '0243 / 02493 digits',
      intro: 'Digits only: find entries sharing the code; 02493 separates the second tone.',
      examples: [
        { label: 'Same-tone matches' },
        { label: '02493 mode — finer second-tone distinction' },
      ],
    },
    examples: [
      { query: '23', mode: 'm1' },
      { query: '93', mode: 'm2' },
    ],
  },
  {
    id: 'ping-ze',
    zh: {
      title: '平仄串列',
      intro:
        '<code translate="no">P</code>＝平（0243 碼 0／3）、<code translate="no">Z</code>＝仄（其餘）；數字＝該格同音。自動切換 <strong>02493模式（緊）</strong>。',
      examples: [
        { label: '二字：平＋仄（如「自己」）' },
        { label: '三字：平仄＋與 3 同音' },
      ],
    },
    en: {
      title: 'Ping–ze serial',
      intro:
        '<code translate="no">P</code> = ping (0243 digits 0/3), <code translate="no">Z</code> = ze (others); a digit = same tone at that slot. Switches to <strong>02493 Mode (Strict)</strong> automatically.',
      examples: [
        { label: 'Two chars: ping + ze (e.g. 自己)' },
        { label: 'Three chars: ping, ze, same as 3' },
      ],
    },
    examples: [
      { query: 'ZP', mode: 'm2' },
      { query: 'PZ3', mode: 'm2' },
    ],
  },
  {
    id: 'serial',
    zh: {
      title: '串列韻／聲錨',
      intro:
        '連續數字：每位一音節碼。<code translate="no">{碼}{字}=</code> 比韻；<code translate="no">{碼}={字}</code> 比聲。<code translate="no">=</code> 永遠喺參考字右側。',
      examples: [
        { label: '二字：碼 23＋尾格同「就」韻' },
        {
          label: '四字：第 2／4 格韻錨',
          title: '串列韻錨：只約束第 2／4 格韻。同 0449窮困潦倒= 唔同（該例要求四字整詞同韻）。',
        },
        { label: '四字：第 2／4 格聲錨' },
        { label: '四字：第 1 格通配＋韻錨' },
        { label: '三字：中格碼 3＋尾格同「人」韻' },
      ],
    },
    en: {
      title: 'Serial rhyme / initial anchors',
      intro:
        'Consecutive digits: one code per syllable. <code translate="no">{code}{char}=</code> matches rhyme; <code translate="no">{code}={char}</code> matches initial. <code translate="no">=</code> always sits to the right of the anchor character.',
      examples: [
        { label: 'Two chars: code 23 + last slot rhymes with 就' },
        {
          label: 'Four chars: rhyme anchors on slots 2 / 4',
          title:
            'Serial rhyme anchors: only slots 2 and 4 are rhyme-constrained. Unlike 0449窮困潦倒= (that example requires the whole four-character word to rhyme).',
        },
        { label: 'Four chars: initial anchors on slots 2 / 4' },
        { label: 'Four chars: wildcard slot 1 + rhyme anchors' },
        { label: 'Three chars: middle code 3 + last slot rhymes with 人' },
      ],
    },
    examples: [
      { query: '23就=', mode: 'm1' },
      { query: '04困=49倒=', mode: 'm1' },
      { query: '04=困49=倒', mode: 'm1' },
      { query: '?4困=4潦=9倒=', mode: 'm1' },
      { query: '?3人=?', mode: 'm1' },
    ],
  },
  {
    id: 'partial',
    zh: {
      title: '四字部分韻／聲錨',
      intro:
        '<code translate="no">?</code> 標通配格；其餘漢字格逐格比韻／聲（結果唔使同骨架逐字相等）。',
      examples: [
        {
          label: '四字：第 2 格通配＋部分韻錨',
          title: '四字部分韻錨：第 2 格通配，窮／潦／倒 各比韻。',
        },
        { label: '四字：第 3 格通配＋部分韻錨' },
        { label: '四字：第 4 格通配＋部分韻錨' },
        { label: '四字：第 2 格通配＋部分聲錨' },
        { label: '四字：第 3 格通配＋部分聲錨' },
        { label: '四字：第 4 格通配＋部分聲錨' },
      ],
    },
    en: {
      title: 'Partial four-character rhyme / initial',
      intro:
        '<code translate="no">?</code> marks a wildcard slot; other character slots are compared rhyme- or initial-wise (results need not match the skeleton character-for-character).',
      examples: [
        {
          label: 'Four chars: wildcard slot 2 + partial rhyme anchors',
          title: 'Partial four-character rhyme: slot 2 is wildcard; 窮, 潦, 倒 each anchor rhyme.',
        },
        { label: 'Four chars: wildcard slot 3 + partial rhyme anchors' },
        { label: 'Four chars: wildcard slot 4 + partial rhyme anchors' },
        { label: 'Four chars: wildcard slot 2 + partial initial anchors' },
        { label: 'Four chars: wildcard slot 3 + partial initial anchors' },
        { label: 'Four chars: wildcard slot 4 + partial initial anchors' },
      ],
    },
    examples: [
      { query: '窮?潦倒=', mode: 'm1' },
      { query: '窮困?倒=', mode: 'm1' },
      { query: '窮困潦=?', mode: 'm1' },
      { query: '=窮?潦倒', mode: 'm1' },
      { query: '=窮困?倒', mode: 'm1' },
      { query: '=窮困潦?', mode: 'm1' },
    ],
  },
  {
    id: 'prefix-wildcard',
    zh: {
      title: '前綴通配等號',
      intro:
        '第 1 格完全通配；其餘音節逐格同參考模板（須尾 <code translate="no">=</code> 表韻）。',
      examples: [
        { label: '三字：第 1 格任意，其餘同「香港」韻' },
        {
          label: '四字：第 1 格任意，其餘同「困潦倒」韻',
          title: '前綴通配等號：第 1 格完全通配，第 2–4 格同「困潦倒」韻模板。',
        },
        {
          label: '四字：第 1 格任意，其餘同「困潦倒」聲',
          title: '前綴通配聲錨：第 1 格通配，其餘格同「困潦倒」聲母。',
        },
      ],
    },
    en: {
      title: 'Prefix wildcard equals',
      intro:
        'Slot 1 is fully wildcarded; remaining syllables follow the reference template (trailing <code translate="no">=</code> means rhyme).',
      examples: [
        { label: 'Three chars: any slot 1; others rhyme like 香港' },
        {
          label: 'Four chars: any slot 1; others rhyme like 困潦倒',
          title: 'Prefix wildcard equals: slot 1 fully wildcarded; slots 2–4 follow the 困潦倒 rhyme template.',
        },
        {
          label: 'Four chars: any slot 1; others share initials with 困潦倒',
          title: 'Prefix wildcard initial: slot 1 wildcarded; remaining slots match 困潦倒 initials.',
        },
      ],
    },
    examples: [
      { query: '?香港=', mode: 'm1' },
      { query: '?困潦倒=', mode: 'm1' },
      { query: '?=困潦倒', mode: 'm1' },
    ],
  },
  {
    id: 'wildcard-code',
    zh: {
      title: '通配碼錨',
      intro:
        '首音節 <code translate="no">?</code> 通配，後接連續碼；尾漢字係韻參考字。加槽用 <code translate="no">+</code>。',
      examples: [
        { label: '三字：碼 30＋尾同「人」韻' },
        { label: '四字：首任意＋30＋多一槽＋同「人」韻' },
      ],
    },
    en: {
      title: 'Wildcard code anchor',
      intro:
        'First syllable <code translate="no">?</code> is wildcarded, then consecutive codes; trailing character is the rhyme reference. Use <code translate="no">+</code> for extra slots.',
      examples: [
        { label: 'Three chars: code 30 + last rhymes with 人' },
        { label: 'Four chars: any first + 30 + extra slot + rhymes with 人' },
      ],
    },
    examples: [
      { query: '?30人', mode: 'm1' },
      { query: '?30+人', mode: 'm1' },
    ],
  },
  {
    id: 'mask',
    zh: {
      title: '缺字／音查詢（遮罩）',
      intro:
        '漢字固定字面，數字固定碼，其餘用 <code translate="no">?</code>／<code translate="no">_</code>／<code translate="no">%</code>。頭格的 <code translate="no">+</code> 可省略。',
      examples: [
        { label: '三字，首格字面「香」' },
        { label: '三字，中格字面「你」' },
        { label: '三字，中格字面「識」' },
        { label: '二字：首字同 3 同音，尾字不限' },
        { label: '三字：頭兩字 23 同音，尾字不限' },
        { label: '二字：首格字面「門」＋尾碼 0（normalize 為 +門0）' },
      ],
    },
    en: {
      title: 'Masked missing-character queries',
      intro:
        'Fix character literals and digit codes; use <code translate="no">?</code> / <code translate="no">_</code> / <code translate="no">%</code> elsewhere. Leading <code translate="no">+</code> may be omitted.',
      examples: [
        { label: 'Three chars: first slot literal 香' },
        { label: 'Three chars: middle slot literal 你' },
        { label: 'Three chars: middle slot literal 識' },
        { label: 'Two chars: first same tone as 3, last unrestricted' },
        { label: 'Three chars: first two share code 23, last unrestricted' },
        { label: 'Two chars: first literal 門 + trailing code 0 (normalizes to +門0)' },
      ],
    },
    examples: [
      { query: '+香??', mode: 'm1' },
      { query: '?+你?', mode: 'm1' },
      { query: '_識_', mode: 'm1' },
      { query: '3_', mode: 'm1' },
      { query: '23?', mode: 'm1' },
      { query: '門0', mode: 'm1' },
    ],
  },
  {
    id: 'plus',
    zh: {
      title: '加號錨（+）',
      intro:
        '<code translate="no">+</code> 連接碼同錨字，標明邊一格。<code translate="no">錨字=</code> 同韻母；<code translate="no">+=錨字</code> 同聲母；無 <code translate="no">=</code> 則字面固定。輸入 <code translate="no">*</code> 等同 <code translate="no">+</code>。',
      examples: [
        { label: '二字：尾字字面固定「就」' },
        { label: '三字：尾格字面「好」' },
        { label: '三字：尾格同「好」同韻母' },
        { label: '三字：尾格同「好」同聲母' },
        { label: '三字：中格字面「好」＋首/尾碼' },
        { label: '三字：中格同「好」同韻母＋首/尾碼' },
        { label: '二字：首格字面「門」＋尾碼 0' },
        { label: '二字：首格同「門」同韻母＋尾碼 0' },
      ],
    },
    en: {
      title: 'Plus-slot anchor (+)',
      intro:
        '<code translate="no">+</code> links codes and anchor characters to mark which slot. <code translate="no">anchor=</code> matches rhyme; <code translate="no">+=anchor</code> matches initial; without <code translate="no">=</code> the literal is fixed. <code translate="no">*</code> is accepted as <code translate="no">+</code>.',
      examples: [
        { label: 'Two chars: fixed literal 就 on last slot' },
        { label: 'Three chars: last slot literal 好' },
        { label: 'Three chars: last slot rhymes with 好' },
        { label: 'Three chars: last slot shares initial with 好' },
        { label: 'Three chars: middle literal 好 + first/last codes' },
        { label: 'Three chars: middle rhymes with 好 + first/last codes' },
        { label: 'Two chars: first literal 門 + trailing code 0' },
        { label: 'Two chars: first rhymes with 門 + trailing code 0' },
      ],
    },
    examples: [
      { query: '23@就', mode: 'm1' },
      { query: '23+好', mode: 'm1' },
      { query: '23+好=', mode: 'm1' },
      { query: '23+=好', mode: 'm1' },
      { query: '2+好3', mode: 'm1' },
      { query: '2+好=3', mode: 'm1' },
      { query: '+門0', mode: 'm1' },
      { query: '+門=0', mode: 'm1' },
    ],
  },
  {
    id: 'rhyme-initial',
    zh: {
      title: '同韻／同聲錨（=）',
      intro:
        '<code translate="no">錨字=</code> 比韻母，<code translate="no">=錨字</code> 比聲母；錨字唔一定出現喺結果。',
      examples: [
        { label: '二字，首字同「香」同韻' },
        { label: '單字，同「就」同韻' },
        { label: '二字，尾字同「就」同韻' },
        { label: '三字，中格同「港」同韻（?港=? 等價）' },
        { label: '二字，首字同「香」同聲' },
        { label: '二字，尾字同「就」同聲' },
      ],
    },
    en: {
      title: 'Rhyme / initial anchor (=)',
      intro:
        '<code translate="no">anchor=</code> matches rhyme; <code translate="no">=anchor</code> matches initial; the anchor character need not appear in results.',
      examples: [
        { label: 'Two chars: first rhymes with 香' },
        { label: 'Single character rhyming with 就' },
        { label: 'Two chars: last rhymes with 就' },
        { label: 'Three chars: middle rhymes with 港 (?港=? equivalent)' },
        { label: 'Two chars: first shares initial with 香' },
        { label: 'Two chars: last shares initial with 就' },
      ],
    },
    examples: [
      { query: '香=?', mode: 'm1' },
      { query: '就=', mode: 'm1' },
      { query: '?+就=', mode: 'm1' },
      { query: '?+港=?', mode: 'm1' },
      { query: '=香?', mode: 'm1' },
      { query: '?=就', mode: 'm1' },
    ],
  },
  {
    id: 'jyutping-anchor',
    zh: {
      title: '粵拼錨',
      intro:
        '缺字族用拉丁拼標韻母、音節或聲母；slot 連接用 <code translate="no">+</code>（如 <code translate="no">?+hon</code>、<code translate="no">3+ngo4</code>）。',
      examples: [
        { label: '二字，末格音節 hon' },
        { label: '三字，中格韻母 yut' },
        { label: '三字，中格音節 syut' },
        { label: '三字，首碼＋音節＋末碼' },
        { label: '二字，碼 34，首格音節 hon' },
        { label: '同上（漢字音節錨，≡ 3hon4）' },
        { label: '二字，碼 34，首格聲母 h' },
        { label: '二字，碼 34，首格雙聲母 gw' },
        { label: '二字，碼 23，末格韻母 o' },
        { label: '三字，碼 23＋尾格韻母 o' },
        { label: '三字，碼 230，中格韻母 ei' },
        { label: '三字，中格 m／ng 雙列' },
        { label: '二字碼 34，首格 m／ng 雙列' },
      ],
    },
    en: {
      title: 'Jyutping anchors',
      intro:
        'In masked queries, use Latin letters for finals, syllables, or initials; connect slots with <code translate="no">+</code> (e.g. <code translate="no">?+hon</code>, <code translate="no">3+ngo4</code>).',
      examples: [
        { label: 'Two chars: last slot syllable hon' },
        { label: 'Three chars: middle final yut' },
        { label: 'Three chars: middle syllable syut' },
        { label: 'Three chars: leading code + syllable + trailing code' },
        { label: 'Two chars: code 34, first slot syllable hon' },
        { label: 'Same (Hanzi syllable anchor, ≡ 3hon4)' },
        { label: 'Two chars: code 34, first initial h' },
        { label: 'Two chars: code 34, first digraph initial gw' },
        { label: 'Two chars: code 23, last final o' },
        { label: 'Three chars: code 23 + last final o' },
        { label: 'Three chars: code 230, middle final ei' },
        { label: 'Three chars: middle m / ng dual column' },
        { label: 'Two-char code 34, first m / ng dual column' },
      ],
    },
    examples: [
      { query: '?+hon', mode: 'm1' },
      { query: '?+yut?', mode: 'm1' },
      { query: '?+syut?', mode: 'm1' },
      { query: '3+ngo4', mode: 'm1' },
      { query: '3hon4', mode: 'm1' },
      { query: '3$漢4', mode: 'm1' },
      { query: '3h4', mode: 'm1' },
      { query: '3gw4', mode: 'm1' },
      { query: '23o', mode: 'm1' },
      { query: '23+o', mode: 'm1' },
      { query: '23ei0', mode: 'm1' },
      { query: '?+m?', mode: 'm1' },
      { query: '3m4', mode: 'm1' },
    ],
  },
  {
    id: 'equals',
    zh: {
      title: '整詞／碼夾等號（=）',
      intro:
        '詞尾 <code translate="no">=</code> 比整詞韻，詞首 <code translate="no">=</code> 比整詞聲；碼夾約束單格。<code translate="no">{左碼}{全詞}=</code>（碼長=字數）再加 0243 碼約束。',
      examples: [
        {
          label: '四字：碼 0449＋整詞同「窮困潦倒」韻',
          title: '填滿 code+全詞；要求四字整詞同韻且碼 0449。同 04困=49倒= 唔同（該例只韻錨第 2／4 格）。',
        },
        { label: '二字，整詞同「香港」同韻' },
        { label: '二字，23同音，首字同「我」同韻' },
        { label: '三字，碼 23＋尾格同「就」同韻' },
        { label: '二字，整詞同「香港」同聲' },
        { label: '二字，23同音，首字同「我」同聲' },
      ],
    },
    en: {
      title: 'Whole-word / code-sandwich equals (=)',
      intro:
        'Trailing <code translate="no">=</code> matches whole-word rhyme; leading <code translate="no">=</code> matches whole-word initials; code sandwich constrains one slot. <code translate="no">{leftCode}{fullWord}=</code> (code length = character count) adds a 0243 code constraint.',
      examples: [
        {
          label: 'Four chars: code 0449 + whole word rhymes like 窮困潦倒',
          title:
            'Full code + full word: four-character whole-word rhyme with code 0449. Unlike 04困=49倒= (that example only rhyme-anchors slots 2 / 4).',
        },
        { label: 'Two chars: whole word rhymes like 香港' },
        { label: 'Two chars: code 23 homophone, first rhymes with 我' },
        { label: 'Three chars: code 23 + last rhymes with 就' },
        { label: 'Two chars: whole word shares initials with 香港' },
        { label: 'Two chars: code 23 homophone, first shares initial with 我' },
      ],
    },
    examples: [
      { query: '0449窮困潦倒=', mode: 'm1' },
      { query: '香港=', mode: 'm1' },
      { query: '2我=3', mode: 'm1' },
      { query: '23+就=', mode: 'm1' },
      { query: '=香港', mode: 'm1' },
      { query: '2=我3', mode: 'm1' },
    ],
  },
  {
    id: 'relation',
    zh: {
      title: '近義 / 反義',
      intro:
        '<code translate="no">~</code> 近義、<code translate="no">!</code> 反義；可加碼前綴。僅 0243／02493 模式。',
      examples: [
        { label: '近義於「開心」' },
        { label: '反義於「你」（含鏡像近義）' },
        { label: '33同音 + 反義於「開心」' },
      ],
    },
    en: {
      title: 'Synonym / antonym',
      intro:
        '<code translate="no">~</code> near-synonym, <code translate="no">!</code> antonym; optional code prefix. 0243 / 02493 modes only.',
      examples: [
        { label: 'Near-synonyms of 開心' },
        { label: 'Antonyms of 你 (includes mirrored near-synonyms)' },
        { label: 'Code 33 homophone + antonyms of 開心' },
      ],
    },
    examples: [
      { query: '~開心', mode: 'm1' },
      { query: '!你', mode: 'm1' },
      { query: '33!開心', mode: 'm1' },
    ],
  },
  {
    id: 'syn-pool',
    zh: {
      title: '近反義池',
      intro: '近反義模式：輸入漢字瀏覽近義、反義與語意相關詞條。',
      examples: [{ label: '瀏覽「開心」嘅近反義池' }],
    },
    en: {
      title: 'Synonym / antonym pool',
      intro: 'Synonym/antonym mode: enter a character to browse near-synonyms, antonyms, and related words.',
      examples: [{ label: 'Browse the relation pool for 開心' }],
    },
    examples: [{ query: '開心', mode: 'syn' }],
  },
  {
    id: 'compound-syn',
    zh: {
      title: '近義複合詞',
      intro: '<code translate="no">~~</code> 搵二字近義複合；可加碼前綴或尾韻字。',
      examples: [
        { label: '二字近義複合（如朋友、恐懼）' },
        { label: '33同音 + 近義複合' },
        { label: '近義複合，尾字同「你」同韻' },
        { label: '33同音 + 近義複合 + 尾字同「你」同韻' },
      ],
    },
    en: {
      title: 'Near-synonym compounds',
      intro: '<code translate="no">~~</code> finds two-character near-synonym compounds; optional code prefix or trailing rhyme character.',
      examples: [
        { label: 'Two-char near-synonym compound (e.g. 朋友, 恐懼)' },
        { label: 'Code 33 homophone + near-synonym compound' },
        { label: 'Near-synonym compound; last char rhymes with 你' },
        { label: 'Code 33 + near-synonym compound + last rhymes with 你' },
      ],
    },
    examples: [
      { query: '~~', mode: 'm1' },
      { query: '33~~', mode: 'm1' },
      { query: '~~你', mode: 'm1' },
      { query: '33~~你', mode: 'm1' },
    ],
  },
  {
    id: 'compound-ant',
    zh: {
      title: '反義複合詞',
      intro: '<code translate="no">!!</code> 搵二字反義複合；可加碼前綴或尾韻字。',
      examples: [
        { label: '二字反義複合（如生死、是非）' },
        { label: '33同音 + 反義複合' },
        { label: '反義複合，尾字同「你」同韻' },
        { label: '33同音 + 反義複合 + 尾字同「你」同韻' },
      ],
    },
    en: {
      title: 'Antonym compounds',
      intro: '<code translate="no">!!</code> finds two-character antonym compounds; optional code prefix or trailing rhyme character.',
      examples: [
        { label: 'Two-char antonym compound (e.g. 生死, 是非)' },
        { label: 'Code 33 homophone + antonym compound' },
        { label: 'Antonym compound; last char rhymes with 你' },
        { label: 'Code 33 + antonym compound + last rhymes with 你' },
      ],
    },
    examples: [
      { query: '!!', mode: 'm1' },
      { query: '33!!', mode: 'm1' },
      { query: '!!你', mode: 'm1' },
      { query: '33!!你', mode: 'm1' },
    ],
  },
  {
    id: 'doubled',
    zh: {
      title: '雙聲疊韻字',
      intro:
        '連續 <code translate="no">$</code> 的個數 = 詞長（2–4）；各字音節相同（聲調不限）；可加碼前綴或尾韻字。語法鏡像 <code translate="no">~~</code>。',
      examples: [
        { label: '二字（如慢慢、識食）' },
        { label: '三字（如哈哈哈）' },
        { label: '四字同音節詞' },
        { label: '碼 33 + 二字雙聲疊韻字' },
        { label: '碼 333 + 三字雙聲疊韻字' },
        { label: '二字，尾字同「你」同韻' },
      ],
    },
    en: {
      title: 'Reduplicated same-syllable words',
      intro:
        'Count of consecutive <code translate="no">$</code> = word length (2–4); each character shares the same syllable (any tone); optional code prefix or trailing rhyme char. Syntax mirrors <code translate="no">~~</code>.',
      examples: [
        { label: 'Two chars (e.g. 慢慢, 識食)' },
        { label: 'Three chars (e.g. 哈哈哈)' },
        { label: 'Four-char same-syllable word' },
        { label: 'Code 33 + two-char reduplication' },
        { label: 'Code 333 + three-char reduplication' },
        { label: 'Two chars; last rhymes with 你' },
      ],
    },
    examples: [
      { query: '$$', mode: 'm1' },
      { query: '$$$', mode: 'm1' },
      { query: '$$$$', mode: 'm1' },
      { query: '33$$', mode: 'm1' },
      { query: '333$$$', mode: 'm1' },
      { query: '$$你', mode: 'm1' },
    ],
  },
  {
    id: 'heteronym',
    zh: {
      title: '同音異讀',
      intro:
        '<code translate="no">{左碼}/{右碼}</code> 搵同一字面、至少兩個唔同粵拼讀音；<code translate="no">?</code> 通配碼位。僅 0243／02493 模式。',
      examples: [
        { label: '二字異讀（如「今晚」gam1 maan1／gam1 maan5）' },
        { label: '只約束第 2 字碼 3／4' },
        { label: '單字異讀（如「上」soeng5／soeng6）' },
      ],
    },
    en: {
      title: 'Heteronym (variant readings)',
      intro:
        '<code translate="no">{leftCode}/{rightCode}</code> finds the same written form with at least two Jyutping readings; <code translate="no">?</code> wildcards a code slot. 0243 / 02493 modes only.',
      examples: [
        { label: 'Two-char variant (e.g. 今晚 gam1 maan1 / gam1 maan5)' },
        { label: 'Only constrain 2nd character code 3 / 4' },
        { label: 'Single-character variant (e.g. 上 soeng5 / soeng6)' },
      ],
    },
    examples: [
      { query: '33/34', mode: 'm1' },
      { query: '?3/?4', mode: 'm1' },
      { query: '3/4', mode: 'm1' },
    ],
  },
  {
    id: 'connective',
    zh: {
      title: '連接詞複合詞',
      intro:
        '中格填詞連接詞（與、和、或…）嘅三字複合；<code translate="no">~與~</code> 近義、<code translate="no">!與!</code> 反義。',
      examples: [
        { label: '反義連接詞複合（如生與死）' },
        { label: '近義連接詞複合' },
      ],
    },
    en: {
      title: 'Connective compounds',
      intro:
        'Three-character compounds with a connective in the middle (與, 和, 或…); <code translate="no">~與~</code> near-synonym, <code translate="no">!與!</code> antonym.',
      examples: [
        { label: 'Antonym connective compound (e.g. 生與死)' },
        { label: 'Near-synonym connective compound' },
      ],
    },
    examples: [
      { query: '!與!', mode: 'm1' },
      { query: '~與~', mode: 'm1' },
    ],
  },
];

const GUIDE_HERO = {
  zh: {
    eyebrow: 'Search manual',
    title: '所有搜尋語法',
    lede:
      '每個例子都可以直接執行。點擊後會回到搜尋頁、套用建議模式，並送出查詢。<strong>口訣：</strong><code translate="no">=</code> 在錨字<strong>後</strong> → 韻母；在錨字<strong>前</strong> → 聲母（一般查詢與 <code translate="no">+</code> 延伸段相同）。',
  },
  en: {
    eyebrow: 'Search manual',
    title: 'All search syntax',
    lede:
      'Every example is clickable. Tap one to return to search, apply the suggested mode, and run the query. <strong>Mnemonic:</strong> <code translate="no">=</code> <strong>after</strong> the anchor → rhyme; <strong>before</strong> the anchor → initial (same rule for general queries and <code translate="no">+</code> extensions).',
  },
};

const GUIDE_INTRO = {
  zh: {
    title: '基本說明',
    paragraphs: [
      '<strong>打數字，搵 0243 碼同音嘅詞條。</strong>每個數字對應一個音節嘅聲調（0243 碼），查詢有幾個數字就搵幾個音節嘅詞。例如打「23」，會搵整詞 0243 碼同「23」同音嘅二字詞，包括「自己」、「第一」、「做好」。打「232」會搵三字同音詞，例如「是不是」、「自己做」、「沒關係」。<strong>0243模式</strong>用 0243 碼；<strong>02493模式</strong>用 02493，調值更細（分清二聲）。<strong>平仄串列</strong>用 <code translate="no">P</code>（平）／<code translate="no">Z</code>（仄）同數字混寫（如 <code translate="no">PZ3</code>），會自動切換 02493模式。',
      '<strong>打漢字，查詞條讀音同編碼。</strong>例如打「開心」、「明白」、「食飯」，會見到粵拼、0243 碼，以及同音候選。切換<strong>近反義模式</strong>，可以直接列出該詞嘅近義、反義同語意相關字。',
      '<strong>打數字加錨字，逐格約束韻或聲。</strong>串列掃描：每位數字一音節碼，<code translate="no">{碼}{字}=</code> 韻錨、<code translate="no">{碼}={字}</code> 聲錨。例 <code translate="no">23就=</code>（二字尾格同「就」韻）、<code translate="no">04困=49倒=</code>（四字韻錨）。加槽用 <code translate="no">+</code>，如 <code translate="no">23+就=</code>（三字尾格同韻）；尾字字面固定用 <code translate="no">23@就</code>。',
      '<strong>缺字同加長位置。</strong>通配用 <code translate="no">?</code>／<code translate="no">_</code>／<code translate="no">%</code>；加槽用 <code translate="no">+</code>，例 <code translate="no">+香??</code>、<code translate="no">23+就</code>、<code translate="no">?30+人</code>。輸入 <code translate="no">*</code> 仍接受（等同 <code translate="no">+</code>）。',
      '<strong>打幾個漢字加等號，搵「同韻」或「同聲」。</strong>打「開心=」會搵整詞逐音節同「開心」同韻嘅詞。打「=最好」會搵整詞逐音節同「最好」同聲嘅詞。單格聲母錨打「=我?」、「?=就」。碼夾等號如「2我=3」、「2=我3」，可同時約束 0243 碼同一格聲或韻。',
      '<strong>打一個漢字加等號，搵「同韻」或「同聲」詞。</strong>打「就=?」會搵首字同「就」同韻嘅二字詞；打「就=」會搵同「就」同韻嘅單字。聲母錨打「=就?」、「?=你」。<strong>口訣：</strong>「=」在錨字後比韻母，在錨字前比聲母。',
      '<strong>打粵拼，精準搵漢字。</strong>冇聲調如「syut」，搵粵拼相同嘅單字（忽略聲調）；有聲調「ming4 baak6」會搵準確讀音嘅字「明白」。近反義模式唔收粵拼，請改打漢字或切換 0243模式／02493模式。',
      '<strong>打粵拼錨，唔使打漢字參考字。</strong>規範形如 <code translate="no">?+yut?</code>、<code translate="no">?+hon</code>、<code translate="no">3+ngo4</code>、<code translate="no">23o</code>（二字韻母）／<code translate="no">23+o</code>（三字碼尾韻母）。<code translate="no">?+m?</code>、<code translate="no">3m4</code> 會分聲母／韻母兩列。',
      '<strong>近義、反義同複合詞（0243模式／02493模式）。</strong>打「~開心」搵同「開心」近義嘅詞；打「!開心」搵反義詞。可加前綴0243碼，例如「33!開心」。打「~~」搵二字<strong>近義複合</strong>（如「朋友」「恐懼」）；打「!!」搵二字<strong>反義複合</strong>（如「生死」「是非」）。語法對稱：<code translate="no">~~</code>／<code translate="no">33~~</code>／<code translate="no">~~你</code>／<code translate="no">33~~你</code>，與 <code translate="no">!!</code> 系列相同。以上複合詞查詢<strong>不適用近反義模式</strong>。',
      '下面每張卡有<strong>可點擊例子</strong>，撳一下就會回到搜尋頁並自動執行。',
    ],
  },
  en: {
    title: 'Basics',
    paragraphs: [
      '<strong>Type digits to find entries sharing a 0243 tone code.</strong> Each digit is one syllable’s tone (0243 code); as many digits as you type, that many syllables are matched. For example <code translate="no">23</code> finds two-character words whose full 0243 code matches <code translate="no">23</code>—such as 自己, 第一, 做好. <code translate="no">232</code> finds three-syllable matches like 是不是, 自己做, 沒關係. <strong>0243 mode</strong> uses 0243 codes; <strong>02493 mode</strong> uses 02493 for finer distinction (separates the second tone). <strong>Ping–ze serial</strong> mixes <code translate="no">P</code> (ping) / <code translate="no">Z</code> (ze) with digits (e.g. <code translate="no">PZ3</code>) and switches to 02493 mode automatically.',
      '<strong>Type Chinese characters to look up readings and codes.</strong> Enter 開心, 明白, 食飯 to see Jyutping, 0243 codes, and same-tone candidates. Switch to <strong>synonym/antonym mode</strong> to list near-synonyms, antonyms, and semantically related words.',
      '<strong>Digits plus anchor characters constrain rhyme or initial per slot.</strong> Serial scan: one code digit per syllable; <code translate="no">{code}{char}=</code> rhyme anchor, <code translate="no">{code}={char}</code> initial anchor. E.g. <code translate="no">23就=</code> (two chars: last rhymes with 就), <code translate="no">04困=49倒=</code> (four-char rhyme anchors). Extra slots use <code translate="no">+</code>, e.g. <code translate="no">23+就=</code> (three chars: last rhymes); fix the last literal with <code translate="no">23@就</code>.',
      '<strong>Missing characters and extra slots.</strong> Wildcards: <code translate="no">?</code> / <code translate="no">_</code> / <code translate="no">%</code>; extra slots: <code translate="no">+</code>, e.g. <code translate="no">+香??</code>, <code translate="no">23+就</code>, <code translate="no">?30+人</code>. <code translate="no">*</code> is still accepted (same as <code translate="no">+</code>).',
      '<strong>Several characters plus <code translate="no">=</code> for whole-word rhyme or initial.</strong> <code translate="no">開心=</code> finds words where each syllable rhymes with 開心. <code translate="no">=最好</code> finds words sharing initials with 最好. Single-slot initial anchors: <code translate="no">=我?</code>, <code translate="no">?=就</code>. Code sandwiches like <code translate="no">2我=3</code>, <code translate="no">2=我3</code> constrain both 0243 code and one slot’s rhyme or initial.',
      '<strong>One character plus <code translate="no">=</code> for rhyme- or initial-matched words.</strong> <code translate="no">就=?</code> finds two-character words whose first syllable rhymes with 就; <code translate="no">就=</code> finds single characters rhyming with 就. Initial anchors: <code translate="no">=就?</code>, <code translate="no">?=你</code>. <strong>Mnemonic:</strong> <code translate="no">=</code> after the anchor compares rhyme; before the anchor compares initial.',
      '<strong>Type Jyutping for precise character lookup.</strong> Without tones (e.g. <code translate="no">syut</code>) matches any tone with the same spelling; with tones (<code translate="no">ming4 baak6</code>) matches 明白 exactly. Synonym/antonym mode does not accept Jyutping—use characters or switch to 0243 / 02493 mode.',
      '<strong>Jyutping anchors without a Hanzi reference.</strong> Forms like <code translate="no">?+yut?</code>, <code translate="no">?+hon</code>, <code translate="no">3+ngo4</code>, <code translate="no">23o</code> (two-char final) / <code translate="no">23+o</code> (three-char trailing final). <code translate="no">?+m?</code>, <code translate="no">3m4</code> split into m / ng dual columns.',
      '<strong>Synonyms, antonyms, and compounds (0243 / 02493 modes).</strong> <code translate="no">~開心</code> finds near-synonyms of 開心; <code translate="no">!開心</code> finds antonyms. Optional code prefix, e.g. <code translate="no">33!開心</code>. <code translate="no">~~</code> finds two-character <strong>near-synonym compounds</strong> (e.g. 朋友, 恐懼); <code translate="no">!!</code> finds <strong>antonym compounds</strong> (e.g. 生死, 是非). Symmetric forms: <code translate="no">~~</code> / <code translate="no">33~~</code> / <code translate="no">~~你</code> / <code translate="no">33~~你</code>, same as the <code translate="no">!!</code> family. Compound queries <strong>do not apply in synonym/antonym mode</strong>.',
      'Each card below has <strong>clickable examples</strong>—tap to return to search and run automatically.',
    ],
  },
};

function resolveLang(lang) {
  return lang === 'en' ? 'en' : 'zh';
}

function renderCardTitle(title) {
  return title
    .replace(/（\+）/g, '（<code translate="no">+</code>）')
    .replace(/（=）/g, '（<code translate="no">=</code>）');
}

export function getGuideHero(lang) {
  return GUIDE_HERO[resolveLang(lang)];
}

export function getGuideIntro(lang) {
  return GUIDE_INTRO[resolveLang(lang)];
}

export function getGuideSections(lang) {
  const l = resolveLang(lang);
  return SECTIONS.map((section) => ({
    id: section.id,
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

export function renderGuideGridHtml(lang) {
  const l = resolveLang(lang);
  return SECTIONS.map((section) => {
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
    return (
      `<article class="guide-card">` +
      `<h2>${renderCardTitle(copy.title)}</h2>` +
      `<p>${copy.intro}</p>` +
      `<div class="guide-examples">\n            ${buttons}\n          </div>` +
      `</article>`
    );
  }).join('\n\n        ');
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
  const grid = document.getElementById('guideGrid');
  if (grid) grid.innerHTML = renderGuideGridHtml(l);
}