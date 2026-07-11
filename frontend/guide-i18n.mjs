const SECTIONS = [
  {
    id: 'basic',
    group: 'common',
    zh: {
      title: '基本查詢',
      intro:
        '漢字、詞語、394052 碼或粵拼。',
      examples: [
        { label: '查呢個字嘅所有讀音' },
        { label: '查呢個詞語' },
        { label: '粵拼查詢（冇聲調）' },
        { label: '粵拼查詢（有聲調）' },
      ],
    },
    en: {
      title: 'Basic lookup',
      intro:
        'Chinese characters, words, 394052 codes, or Jyutping.',
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
    group: 'common',
    zh: {
      title: '0243 / 02493 / 394052 數字',
      intro:
        '純數字搵同碼詞條；02493 分清二聲；394052 六聲碼三／五聲分明。',
      examples: [
        { label: '找同音字' },
        { label: '02493模式 分清二聲' },
        { label: '394052模式 三／五聲分明' },
      ],
    },
    en: {
      title: '0243 / 02493 / 394052 digits',
      intro:
        'Digits only: find entries sharing the code; 02493 separates the second tone; 394052 6-tone codes keep tones 3 and 5 distinct.',
      examples: [
        { label: 'Same-tone matches' },
        { label: '02493 mode — finer second-tone distinction' },
        { label: '394052 mode — strict tone-3 vs tone-5 digits' },
      ],
    },
    examples: [
      { query: '23', mode: 'm1' },
      { query: '93', mode: 'm2' },
      { query: '45', mode: 'm3' },
    ],
  },
  {
    id: 'equals',
    group: 'common',
    zh: {
      title: '同韻／同聲（=）',
      intro:
        '字後面加 <code translate="no">=</code> → 同韻；字前面加 <code translate="no">=</code> → 同聲。可整詞用，亦可數字夾住一個字同時規定聲調。參考字唔一定出現喺結果。',
      examples: [
        { label: '單字，同「就」同韻' },
        { label: '二字，首字同「香」同韻' },
        { label: '二字，尾字同「就」同聲' },
        { label: '二字，整詞同「香港」同韻' },
        { label: '二字，整詞同「香港」同聲' },
        { label: '二字：聲調 23，頭字同「我」同韻' },
        { label: '二字：聲調 23，頭字同「我」同聲' },
        { label: '二字，尾字同「就」同韻' },
      ],
    },
    en: {
      title: 'Same rhyme / initial (=)',
      intro:
        'Put <code translate="no">=</code> after a character for rhyme; before it for initial. Works on a whole word, or with tone digits around one character. The reference character need not appear in results.',
      examples: [
        { label: 'Single character rhyming with 就' },
        { label: 'Two chars: first rhymes with 香' },
        { label: 'Two chars: last shares initial with 就' },
        { label: 'Two chars: whole word rhymes like 香港' },
        { label: 'Two chars: whole word shares initials with 香港' },
        { label: 'Two chars: tones 23; first rhymes with 我' },
        { label: 'Two chars: tones 23; first shares initial with 我' },
        { label: 'Two chars: last rhymes with 就' },
      ],
    },
    examples: [
      { query: '就=', mode: 'm1' },
      { query: '香=?', mode: 'm1' },
      { query: '?=就', mode: 'm1' },
      { query: '香港=', mode: 'm1' },
      { query: '=香港', mode: 'm1' },
      { query: '2我=3', mode: 'm1' },
      { query: '2=我3', mode: 'm1' },
      { query: '?+就=', mode: 'm1' },
    ],
  },
  {
    id: 'mask',
    group: 'common',
    zh: {
      title: '有啲字定死、有啲留空',
      intro:
        '寫死你要嘅漢字或聲調數字；唔知嘅位用 <code translate="no">?</code>／<code translate="no">_</code>／<code translate="no">%</code>（三個一樣）。開頭嘅 <code translate="no">+</code> 可以唔打。',
      examples: [
        { label: '三字，第一個字一定係「香」' },
        { label: '三字，中間一定係「你」' },
        { label: '三字，中間一定係「識」' },
        { label: '二字：頭字同 3 同音，尾字隨便' },
        { label: '三字：頭兩字聲調 23，尾字隨便' },
        { label: '二字：頭字「門」，尾字同 0 同音' },
      ],
    },
    en: {
      title: 'Fix some characters, leave others open',
      intro:
        'Lock the characters or tone digits you know; fill unknowns with <code translate="no">?</code> / <code translate="no">_</code> / <code translate="no">%</code> (all the same). A leading <code translate="no">+</code> is optional.',
      examples: [
        { label: 'Three chars: first must be 香' },
        { label: 'Three chars: middle must be 你' },
        { label: 'Three chars: middle must be 識' },
        { label: 'Two chars: first tone 3; last free' },
        { label: 'Three chars: first two tones 23; last free' },
        { label: 'Two chars: first 門; last tone 0' },
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
    group: 'common',
    zh: {
      title: '用 + 加長或標明位置',
      intro:
        '用 <code translate="no">+</code> 加多一個字，或者標明邊個位置。<code translate="no">字=</code>＝同韻；<code translate="no">+=字</code>＝同聲；冇 <code translate="no">=</code> 就係要呢個字本身。打 <code translate="no">*</code> 等同 <code translate="no">+</code>。',
      examples: [
        { label: '二字：聲調 23，第二個字一定係「手」' },
        { label: '三字：尾字一定係「好」' },
        { label: '三字：尾字同「好」同韻' },
        { label: '三字：尾字同「好」同聲' },
        { label: '三字：中間係「好」，頭尾用數字碼' },
        { label: '三字：中間同「好」同韻，頭尾用數字碼' },
        { label: '二字：頭字「門」，尾字同 0 同音' },
        { label: '二字：頭字同「門」同韻，尾字同 0 同音' },
      ],
    },
    en: {
      title: 'Use + to lengthen or mark a position',
      intro:
        'Use <code translate="no">+</code> to add a character or mark a position. <code translate="no">char=</code> = same rhyme; <code translate="no">+=char</code> = same initial; without <code translate="no">=</code> that exact character is required. <code translate="no">*</code> works like <code translate="no">+</code>.',
      examples: [
        { label: 'Two chars: tones 23; second must be 手' },
        { label: 'Three chars: last must be 好' },
        { label: 'Three chars: last rhymes with 好' },
        { label: 'Three chars: last shares initial with 好' },
        { label: 'Three chars: middle literal 好 + first/last codes' },
        { label: 'Three chars: middle rhymes with 好 + first/last codes' },
        { label: 'Two chars: first literal 門 + trailing code 0' },
        { label: 'Two chars: first rhymes with 門 + trailing code 0' },
      ],
    },
    examples: [
      { query: '23@手', mode: 'm1' },
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
    id: 'serial',
    group: 'advanced',
    zh: {
      title: '數字＋參考字：同韻／同聲',
      intro:
        '連續打數字＝每個字一個聲調碼。字後面加 <code translate="no">=</code> → 同韻；字前面加 <code translate="no">=</code> → 同聲。',
      examples: [
        { label: '二字：聲調 23，尾字同「就」同韻' },
        { label: '四字：只規定第 2、第 4 個字同韻', title: '只卡住第 2、第 4 個字嘅韻。同「0449窮困潦倒=」唔同（嗰個係四個字全部同韻）。' },
        { label: '四字：只規定第 2、第 4 個字同聲' },
        { label: '四字：第一個字任意，其餘跟韻' },
        { label: '三字：中間同 3 同音，尾字同「人」同韻' },
      ],
    },
    en: {
      title: 'Digits + reference char: rhyme / initial',
      intro:
        'Type digits in a row — one tone code per character. Put <code translate="no">=</code> after a character for rhyme; before it for initial.',
      examples: [
        { label: 'Two chars: tones 23; last rhymes with 就' },
        { label: 'Four chars: only 2nd and 4th must rhyme', title: 'Only the 2nd and 4th characters are rhyme-locked. Unlike 0449窮困潦倒= (that needs all four to rhyme).' },
        { label: 'Four chars: only 2nd and 4th share initials' },
        { label: 'Four chars: first anything; others rhyme' },
        { label: 'Three chars: middle tone 3; last rhymes with 人' },
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
    group: 'advanced',
    zh: {
      title: '四字：有啲字跟韻／聲，有啲留空',
      intro:
        '用 <code translate="no">?</code> 留空某個字；其餘漢字只要求同韻或同聲（結果唔使同你打嘅字一模一樣）。',
      examples: [
        { label: '四字：第二個字留空，其餘同韻', title: '第二個字隨便；窮／潦／倒 各位要同韻。' },
        { label: '四字：第三個字留空，其餘同韻' },
        { label: '四字：第四個字留空，其餘同韻' },
        { label: '四字：第二個字留空，其餘同聲' },
        { label: '四字：第三個字留空，其餘同聲' },
        { label: '四字：第四個字留空，其餘同聲' },
      ],
    },
    en: {
      title: 'Four chars: some rhyme/initial, some open',
      intro:
        'Use <code translate="no">?</code> to leave a character open; other characters only need matching rhyme or initial (results need not equal your skeleton word).',
      examples: [
        { label: 'Four chars: leave 2nd open; others rhyme', title: '2nd character free; 窮 / 潦 / 倒 each set the rhyme.' },
        { label: 'Four chars: leave 3rd open; others rhyme' },
        { label: 'Four chars: leave 4th open; others rhyme' },
        { label: 'Four chars: leave 2nd open; others same initial' },
        { label: 'Four chars: leave 3rd open; others same initial' },
        { label: 'Four chars: leave 4th open; others same initial' },
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
    group: 'advanced',
    zh: {
      title: '第一個字任意，其餘跟某詞同韻／同聲',
      intro:
        '第一個字隨便；後面幾個字跟你寫嘅詞逐字同韻（詞尾要有 <code translate="no">=</code>）或同聲（詞頭 <code translate="no">=</code>）。',
      examples: [
        { label: '三字：頭字任意，其餘同「香港」同韻' },
        { label: '四字：頭字任意，其餘同「困潦倒」同韻', title: '第一個字隨便；第 2–4 個字同「困潦倒」逐字同韻。' },
        { label: '四字：頭字任意，其餘同「困潦倒」同聲', title: '第一個字隨便；其餘同「困潦倒」逐字同聲母。' },
      ],
    },
    en: {
      title: 'Any first character; rest follow a word',
      intro:
        'First character free; the rest follow your sample word for rhyme (trailing <code translate="no">=</code>) or initial (leading <code translate="no">=</code>).',
      examples: [
        { label: 'Three chars: any first; rest rhyme like 香港' },
        { label: 'Four chars: any first; rest rhyme like 困潦倒', title: 'First character free; chars 2–4 rhyme with 困潦倒 one-by-one.' },
        { label: 'Four chars: any first; rest share initials with 困潦倒', title: 'First character free; the rest match 困潦倒 initials.' },
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
    group: 'advanced',
    zh: {
      title: '任意字＋數字碼＋尾字同韻',
      intro:
        '開頭用 <code translate="no">?</code> 表示第一個字隨便，再打聲調數字；最後一個漢字決定尾字要同邊個同韻。想再多一個字就加 <code translate="no">+</code>。',
      examples: [
        { label: '三字：聲調 30，尾字同「人」同韻' },
        { label: '四字：頭字任意＋30，再加多一個字，尾同「人」韻' },
      ],
    },
    en: {
      title: 'Any char + tone digits + last rhymes',
      intro:
        'Leading <code translate="no">?</code> leaves the first character open, then tone digits; the last character sets the rhyme for the end. Add <code translate="no">+</code> for one more character.',
      examples: [
        { label: 'Three chars: tones 30; last rhymes with 人' },
        { label: 'Four chars: any first + 30 + one more; last rhymes with 人' },
      ],
    },
    examples: [
      { query: '?30人', mode: 'm1' },
      { query: '?30+人', mode: 'm1' },
    ],
  },
  {
    id: 'jyutping-anchor',
    group: 'advanced',
    zh: {
      title: '用粵拼指定某個字',
      intro:
        '唔想打漢字參考字時，可以用粵拼字母標明某個字嘅韻母、完整音節或聲母；位置之間用 <code translate="no">+</code>（如 <code translate="no">?+hon</code>、<code translate="no">3+ngo4</code>）。',
      examples: [
        { label: '二字，尾字音節 hon' },
        { label: '三字，中間韻母 yut' },
        { label: '三字，中間音節 syut' },
        { label: '三字，首碼＋音節＋末碼' },
        { label: '二字，聲調 34，頭字音節 hon' },
        { label: '同上（用漢字標音節，等同 3hon4）' },
        { label: '二字，聲調 34，頭字聲母 h' },
        { label: '二字，聲調 34，頭字聲母 gw' },
        { label: '二字，聲調 23，尾字韻母 o' },
        { label: '三字，聲調 23＋尾字韻母 o' },
        { label: '三字，聲調 230，中間韻母 ei' },
        { label: '三字，中間 m／ng 兩種讀法' },
        { label: '二字聲調 34，頭字 m／ng 兩種讀法' },
      ],
    },
    en: {
      title: 'Specify a syllable with Jyutping',
      intro:
        'Instead of a Chinese reference character, type Jyutping letters for a final, full syllable, or initial; join positions with <code translate="no">+</code> (e.g. <code translate="no">?+hon</code>, <code translate="no">3+ngo4</code>).',
      examples: [
        { label: 'Two chars: last syllable hon' },
        { label: 'Three chars: middle final yut' },
        { label: 'Three chars: middle syllable syut' },
        { label: 'Three chars: leading code + syllable + trailing code' },
        { label: 'Two chars: tones 34, first syllable hon' },
        { label: 'Same (Hanzi marks the syllable, ≡ 3hon4)' },
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
    id: 'ping-ze',
    group: 'advanced',
    zh: {
      title: '平仄（平／仄）',
      intro:
        '<code translate="no">P</code>＝平、<code translate="no">Z</code>＝仄；數字＝嗰個字要同呢個聲調同音。平仄模式下可喺搜尋欄下切換 <strong>0243</strong>／<strong>02493</strong>／<strong>394052</strong>；P／Z 一律按六聲判定。',
      examples: [
        { label: '二字：平＋仄（如「自己」）' },
        { label: '三字：平仄＋第三個字同 3 同音' },
        { label: '平仄之後，尾字同「好」同韻' },
        { label: '頭字同「好」同聲，再接平仄' },
      ],
    },
    en: {
      title: 'Ping / ze pattern',
      intro:
        '<code translate="no">P</code> = ping, <code translate="no">Z</code> = ze; a digit means that character must match that tone. In ping–ze mode, pick <strong>0243</strong> / <strong>02493</strong> / <strong>394052</strong> under the search box; P/Z always use the 6-tone scale.',
      examples: [
        { label: 'Two chars: ping + ze (e.g. 自己)' },
        { label: 'Three chars: ping, ze, then tone 3' },
        { label: 'After PZ, last char rhymes with 好' },
        { label: 'First shares initial with 好, then PZ' },
      ],
    },
    examples: [
      { query: 'PZ', mode: 'pz' },
      { query: 'PZ3', mode: 'pz' },
      { query: 'PZ好=', mode: 'pz' },
      { query: '=好PZ', mode: 'pz' },
    ],
  },
  {
    id: 'relation',
    group: 'advanced',
    zh: {
      title: '近義 / 反義',
      intro:
        '<code translate="no">~</code> 近義、<code translate="no">!</code> 反義；可加碼前綴。僅 0243搜尋三檔（唔包括近反義模式）。',
      examples: [
        { label: '近義於「開心」' },
        { label: '反義於「苦悶」' },
        { label: '33同音 + 反義於「開心」' },
      ],
    },
    en: {
      title: 'Synonym / antonym',
      intro:
        '<code translate="no">~</code> near-synonym, <code translate="no">!</code> antonym; optional code prefix. 0243 search tiers only (not synonym/antonym mode).',
      examples: [
        { label: 'Near-synonyms of 開心' },
        { label: 'Antonyms of 苦悶' },
        { label: 'Code 33 homophone + antonyms of 開心' },
      ],
    },
    examples: [
      { query: '~開心', mode: 'm1' },
      { query: '!苦悶', mode: 'm1' },
      { query: '33!開心', mode: 'm1' },
    ],
  },
  {
    id: 'syn-pool',
    group: 'advanced',
    zh: {
      title: '近反義模式（瀏覽相關詞）',
      intro:
        '切換近反義模式，打一個詞就列出近義、反義同相關詞。',
      examples: [
        { label: '睇「開心」嘅近義／反義' },
      ],
    },
    en: {
      title: 'Synonym/antonym mode (browse related words)',
      intro:
        'Switch to synonym/antonym mode and type a word to list near-synonyms, antonyms, and related words.',
      examples: [
        { label: 'See near-synonyms / antonyms of 開心' },
      ],
    },
    examples: [
      { query: '開心', mode: 'syn' },
    ],
  },
  {
    id: 'compound-syn',
    group: 'advanced',
    zh: {
      title: '近義複合詞',
      intro:
        '<code translate="no">~~</code> 搵二字近義複合；可加碼前綴或尾韻字。',
      examples: [
        { label: '二字近義複合（如朋友、恐懼）' },
        { label: '33同音 + 近義複合' },
        { label: '近義複合，尾字同「你」同韻' },
        { label: '33同音 + 近義複合 + 尾字同「你」同韻' },
      ],
    },
    en: {
      title: 'Near-synonym compounds',
      intro:
        '<code translate="no">~~</code> finds two-character near-synonym compounds; optional code prefix or trailing rhyme character.',
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
    group: 'advanced',
    zh: {
      title: '反義複合詞',
      intro:
        '<code translate="no">!!</code> 搵二字反義複合；可加碼前綴或尾韻字。',
      examples: [
        { label: '二字反義複合（如生死、是非）' },
        { label: '33同音 + 反義複合' },
        { label: '反義複合，尾字同「你」同韻' },
        { label: '33同音 + 反義複合 + 尾字同「你」同韻' },
      ],
    },
    en: {
      title: 'Antonym compounds',
      intro:
        '<code translate="no">!!</code> finds two-character antonym compounds; optional code prefix or trailing rhyme character.',
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
    group: 'advanced',
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
    group: 'advanced',
    zh: {
      title: '同音異讀',
      intro:
        '<code translate="no">{左碼}/{右碼}</code> 搵同一個寫法、至少兩個唔同讀音；某個聲調位唔限可以用 <code translate="no">?</code>。只喺 0243 搜尋三檔用。',
      examples: [
        { label: '二字異讀（如「今晚」gam1 maan1／gam1 maan5）' },
        { label: '只約束第 2 字碼 3／4' },
        { label: '單字異讀（如「上」soeng5／soeng6）' },
      ],
    },
    en: {
      title: 'Heteronym (variant readings)',
      intro:
        '<code translate="no">{leftCode}/{rightCode}</code> finds the same spelling with at least two readings; use <code translate="no">?</code> where a tone digit can be anything. 0243 search tiers only.',
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
    group: 'advanced',
    zh: {
      title: '連接詞複合詞',
      intro:
        '三個字、中間係連接詞（與、和、或…）；<code translate="no">~與~</code> 近義、<code translate="no">!與!</code> 反義。',
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
      '每個例子都可以直接執行。點擊後會回到搜尋頁、套用建議模式，並送出查詢。<strong>口訣：</strong><code translate="no">=</code> 喺參考字<strong>後面</strong> → 同韻；喺參考字<strong>前面</strong> → 同聲（一般查詢同用 <code translate="no">+</code> 加長時一樣）。',
  },
  en: {
    eyebrow: 'Search manual',
    title: 'All search syntax',
    lede:
      'Every example is clickable. Tap one to return to search, apply the suggested mode, and run the query. <strong>Mnemonic:</strong> <code translate="no">=</code> <strong>after</strong> the reference character → rhyme; <strong>before</strong> it → initial (same for plain queries and <code translate="no">+</code> extensions).',
  },
};

const GUIDE_INTRO = {
  zh: {
    title: '點樣睇呢頁',
    paragraphs: [
      '下面按<strong>常用</strong>同<strong>進階</strong>分組。每張卡嘅例子都可以撳一下直接搜尋。',
      '<strong>口訣：</strong><code translate="no">=</code> 喺參考字<strong>後面</strong> → 同韻；喺參考字<strong>前面</strong> → 同聲。留空用 <code translate="no">?</code>／<code translate="no">_</code>／<code translate="no">%</code>；加長用 <code translate="no">+</code>。',
      '數字碼搵同音；近反義用 <code translate="no">~</code>／<code translate="no">!</code>（或切換近反義模式）。更細嘅組合見各卡說明。',
    ],
  },
  en: {
    title: 'How to read this page',
    paragraphs: [
      'Cards are grouped into <strong>Common</strong> and <strong>Advanced</strong>. Every example is clickable and runs a search.',
      '<strong>Mnemonic:</strong> <code translate="no">=</code> <strong>after</strong> a reference character → rhyme; <strong>before</strong> it → initial. Gaps use <code translate="no">?</code> / <code translate="no">_</code> / <code translate="no">%</code>; lengthen with <code translate="no">+</code>.',
      'Tone digits find same-tone words; synonyms/antonyms use <code translate="no">~</code> / <code translate="no">!</code> (or synonym mode). See each card for finer patterns.',
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

const GUIDE_GROUP_LABEL = {
  zh: { common: '常用', advanced: '進階' },
  en: { common: 'Common', advanced: 'Advanced' },
};

export function getGuideGroupLabel(group, lang) {
  const l = resolveLang(lang);
  return GUIDE_GROUP_LABEL[l][group] || group;
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

export function renderGuideGridHtml(lang) {
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
    parts.push(
      `<article class="guide-card">` +
        `<h3>${renderCardTitle(copy.title)}</h3>` +
        `<p>${copy.intro}</p>` +
        `<div class="guide-examples">\n            ${buttons}\n          </div>` +
        `</article>`,
    );
  }
  return parts.join('\n\n        ');
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
