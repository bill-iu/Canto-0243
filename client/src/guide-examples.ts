/**
 * PWA 搜尋教學 — 範例 manifest（對齊桌面 guide-card + family 覆蓋）
 */
export const GUIDE_FAMILY_IDS = [
  'word_lookup',
  'jyutping_lookup',
  'digit_code',
  'mode_02493',
  'code_char',
  'literal_ref',
  'wildcard_code_anchor',
  'rhyme_initial_anchor',
  'plus_anchor',
  'serial_phoneme',
  'partial_rhyme',
  'partial_initial',
  'prefix_wildcard_equals',
  'prefix_wildcard_initial',
  'mask_query',
  'equals_query',
  'code_sandwich_equals',
  'jyutping_anchor_initial',
  'jyutping_anchor_final',
  'jyutping_anchor_syllable',
  'hanzi_syllable_anchor',
  'relation_lookup',
  'compound_syn',
  'compound_ant',
  'compound_doubled',
  'heteronym_code',
  'connective_compound',
  'syn_pool',
] as const;

export type GuideFamilyId = (typeof GUIDE_FAMILY_IDS)[number];
export type GuideMode = '0243' | '02493' | 'synonym';

export interface GuideExample {
  query: string;
  mode: GuideMode;
  label: string;
  /** 覆蓋 self-check 用；教學加料例可省略 */
  familyId?: GuideFamilyId;
  title?: string;
}

export interface GuideSection {
  id: string;
  title: string;
  intro: string;
  examples: GuideExample[];
}

export const GUIDE_SECTIONS: GuideSection[] = [
  {
    id: 'basic',
    title: '基本查詢',
    intro: '漢字、詞語、0243 碼或粵拼。',
    examples: [
      { query: '就', mode: '0243', label: '查呢個字嘅所有讀音', familyId: 'word_lookup' },
      { query: '你好', mode: '0243', label: '查呢個詞語' },
      { query: 'nei hou', mode: '0243', label: '粵拼查詢（冇聲調）', familyId: 'jyutping_lookup' },
      { query: 'ming4 baak6', mode: '0243', label: '粵拼查詢（有聲調）' },
    ],
  },
  {
    id: 'digit',
    title: '0243 / 02493 數字',
    intro: '純數字搵同碼詞條；02493 分清二聲。',
    examples: [
      { query: '23', mode: '0243', label: '找同音字', familyId: 'digit_code' },
      { query: '93', mode: '02493', label: '02493模式 分清二聲', familyId: 'mode_02493' },
    ],
  },
  {
    id: 'serial',
    title: '串列韻／聲錨',
    intro:
      '連續數字：每位一音節碼。{碼}{字}= 比韻；{碼}={字} 比聲。= 永遠喺參考字右側。',
    examples: [
      { query: '23就', mode: '0243', label: '二字：碼 23＋尾格同「就」韻', familyId: 'code_char' },
      { query: '23就=', mode: '0243', label: '二字：碼 23＋尾格同「就」韻（串列）' },
      {
        query: '04困=49倒=',
        mode: '0243',
        label: '四字：第 2／4 格韻錨',
        familyId: 'serial_phoneme',
        title: '串列韻錨：只約束第 2／4 格韻。同 0449窮困潦倒= 唔同（該例要求四字整詞同韻）。',
      },
      { query: '04=困49=倒', mode: '0243', label: '四字：第 2／4 格聲錨' },
      { query: '?4困=4潦=9倒=', mode: '0243', label: '四字：第 1 格通配＋韻錨' },
      { query: '?3人=?', mode: '0243', label: '三字：中格碼 3＋尾格同「人」韻' },
    ],
  },
  {
    id: 'partial',
    title: '四字部分韻／聲錨',
    intro: '? 標通配格；其餘漢字格逐格比韻／聲（結果唔使同骨架逐字相等）。',
    examples: [
      {
        query: '窮?潦倒=',
        mode: '0243',
        label: '四字：第 2 格通配＋部分韻錨',
        familyId: 'partial_rhyme',
        title: '四字部分韻錨：第 2 格通配，窮／潦／倒 各比韻。',
      },
      { query: '窮困?倒=', mode: '0243', label: '四字：第 3 格通配＋部分韻錨' },
      { query: '窮困潦=?', mode: '0243', label: '四字：第 4 格通配＋部分韻錨' },
      { query: '=窮?潦倒', mode: '0243', label: '四字：第 2 格通配＋部分聲錨', familyId: 'partial_initial' },
      { query: '=窮困?倒', mode: '0243', label: '四字：第 3 格通配＋部分聲錨' },
      { query: '=窮困潦?', mode: '0243', label: '四字：第 4 格通配＋部分聲錨' },
    ],
  },
  {
    id: 'prefix-wildcard',
    title: '前綴通配等號',
    intro: '第 1 格完全通配；其餘音節逐格同參考模板（須尾 = 表韻）。',
    examples: [
      { query: '?香港=', mode: '0243', label: '三字：第 1 格任意，其餘同「香港」韻', familyId: 'prefix_wildcard_equals' },
      {
        query: '?困潦倒=',
        mode: '0243',
        label: '四字：第 1 格任意，其餘同「困潦倒」韻',
        title: '前綴通配等號：第 1 格完全通配，第 2–4 格同「困潦倒」韻模板。',
      },
      {
        query: '?=困潦倒',
        mode: '0243',
        label: '四字：第 1 格任意，其餘同「困潦倒」聲',
        familyId: 'prefix_wildcard_initial',
        title: '前綴通配聲錨：第 1 格通配，其餘格同「困潦倒」聲母。',
      },
    ],
  },
  {
    id: 'wildcard-code',
    title: '通配碼錨',
    intro: '首音節 ? 通配，後接連續碼；尾漢字係韻參考字。加槽用 +。',
    examples: [
      { query: '?30人', mode: '0243', label: '三字：碼 30＋尾同「人」韻', familyId: 'wildcard_code_anchor' },
      { query: '?30+人', mode: '0243', label: '四字：首任意＋30＋多一槽＋同「人」韻' },
    ],
  },
  {
    id: 'mask',
    title: '缺字／音查詢（遮罩）',
    intro: '漢字固定字面，數字固定碼，其餘用 ?／_／%。頭格的 + 可省略。',
    examples: [
      { query: '+香??', mode: '0243', label: '三字，首格字面「香」', familyId: 'mask_query' },
      { query: '?+你?', mode: '0243', label: '三字，中格字面「你」' },
      { query: '_識_', mode: '0243', label: '三字，中格字面「識」' },
      { query: '3_', mode: '0243', label: '二字：首字同 3 同音，尾字不限' },
      { query: '23?', mode: '0243', label: '三字：頭兩字 23 同音，尾字不限' },
      { query: '門0', mode: '0243', label: '二字：首格字面「門」＋尾碼 0（normalize 為 +門0）' },
    ],
  },
  {
    id: 'plus',
    title: '加號錨（+）',
    intro:
      '+ 連接碼同錨字，標明邊一格。錨字= 同韻母；+=錨字 同聲母；無 = 則字面固定。輸入 * 等同 +。',
    examples: [
      { query: '23@就', mode: '0243', label: '二字：尾字字面固定「就」', familyId: 'literal_ref' },
      { query: '23+好', mode: '0243', label: '三字：尾格字面「好」' },
      { query: '23+好=', mode: '0243', label: '三字：尾格同「好」同韻母', familyId: 'plus_anchor' },
      { query: '23+=好', mode: '0243', label: '三字：尾格同「好」同聲母' },
      { query: '2+好3', mode: '0243', label: '三字：中格字面「好」＋首/尾碼' },
      { query: '2+好=3', mode: '0243', label: '三字：中格同「好」同韻母＋首/尾碼' },
      { query: '+門0', mode: '0243', label: '二字：首格字面「門」＋尾碼 0' },
      { query: '+門=0', mode: '0243', label: '二字：首格同「門」同韻母＋尾碼 0' },
    ],
  },
  {
    id: 'rhyme-initial',
    title: '同韻／同聲錨（=）',
    intro: '錨字= 比韻母，=錨字 比聲母；錨字唔一定出現喺結果。',
    examples: [
      { query: '香=?', mode: '0243', label: '二字，首字同「香」同韻' },
      { query: '就=', mode: '0243', label: '單字，同「就」同韻', familyId: 'rhyme_initial_anchor' },
      { query: '?+就=', mode: '0243', label: '二字，尾字同「就」同韻' },
      { query: '?+港=?', mode: '0243', label: '三字，中格同「港」同韻（?港=? 等價）' },
      { query: '=香?', mode: '0243', label: '二字，首字同「香」同聲' },
      { query: '?=就', mode: '0243', label: '二字，尾字同「就」同聲' },
    ],
  },
  {
    id: 'jyutping-anchor',
    title: '粵拼錨',
    intro: '缺字族用拉丁拼標韻母、音節或聲母；slot 連接用 +（如 ?+hon、3+ngo4）。',
    examples: [
      { query: '?+hon', mode: '0243', label: '二字，末格音節 hon' },
      { query: '?+yut?', mode: '0243', label: '三字，中格韻母 yut' },
      { query: '?+syut?', mode: '0243', label: '三字，中格音節 syut' },
      { query: '3+ngo4', mode: '0243', label: '三字，首碼＋音節＋末碼' },
      {
        query: '3hon4',
        mode: '0243',
        label: '二字，碼 34，首格音節 hon',
        familyId: 'jyutping_anchor_syllable',
      },
      { query: '3$漢4', mode: '0243', label: '同上（漢字音節錨，≡ 3hon4）', familyId: 'hanzi_syllable_anchor' },
      { query: '3h4', mode: '0243', label: '二字，碼 34，首格聲母 h', familyId: 'jyutping_anchor_initial' },
      { query: '3gw4', mode: '0243', label: '二字，碼 34，首格雙聲母 gw' },
      { query: '23o', mode: '0243', label: '二字，碼 23，末格韻母 o', familyId: 'jyutping_anchor_final' },
      { query: '23+o', mode: '0243', label: '三字，碼 23＋尾格韻母 o' },
      { query: '23ei0', mode: '0243', label: '三字，碼 230，中格韻母 ei' },
      { query: '?+m?', mode: '0243', label: '三字，中格 m／ng 雙列' },
      { query: '3m4', mode: '0243', label: '二字碼 34，首格 m／ng 雙列' },
    ],
  },
  {
    id: 'equals',
    title: '整詞／碼夾等號（=）',
    intro:
      '詞尾 = 比整詞韻，詞首 = 比整詞聲；碼夾約束單格。{左碼}{全詞}=（碼長=字數）再加 0243 碼約束。',
    examples: [
      {
        query: '0449窮困潦倒=',
        mode: '0243',
        label: '四字：碼 0449＋整詞同「窮困潦倒」韻',
        title: '填滿 code+全詞；要求四字整詞同韻且碼 0449。同 04困=49倒= 唔同（該例只韻錨第 2／4 格）。',
      },
      { query: '香港=', mode: '0243', label: '二字，整詞同「香港」同韻', familyId: 'equals_query' },
      { query: '2我=3', mode: '0243', label: '二字，23同音，首字同「我」同韻', familyId: 'code_sandwich_equals' },
      { query: '23+就=', mode: '0243', label: '三字，碼 23＋尾格同「就」同韻' },
      { query: '=香港', mode: '0243', label: '二字，整詞同「香港」同聲' },
      { query: '2=我3', mode: '0243', label: '二字，23同音，首字同「我」同聲' },
    ],
  },
  {
    id: 'relation',
    title: '近義 / 反義',
    intro: '~ 近義、! 反義；可加碼前綴。僅 0243／02493 模式。',
    examples: [
      { query: '~開心', mode: '0243', label: '近義於「開心」', familyId: 'relation_lookup' },
      { query: '!你', mode: '0243', label: '反義於「你」（含鏡像近義）' },
      { query: '33!開心', mode: '0243', label: '33同音 + 反義於「開心」' },
    ],
  },
  {
    id: 'syn-pool',
    title: '近反義池',
    intro: '近反義模式：輸入漢字瀏覽近義、反義與語意相關詞條。',
    examples: [
      { query: '開心', mode: 'synonym', label: '瀏覽「開心」嘅近反義池', familyId: 'syn_pool' },
    ],
  },
  {
    id: 'compound-syn',
    title: '近義複合詞',
    intro: '~~ 搵二字近義複合；可加碼前綴或尾韻字。',
    examples: [
      { query: '~~', mode: '0243', label: '二字近義複合（如朋友、恐懼）', familyId: 'compound_syn' },
      { query: '33~~', mode: '0243', label: '33同音 + 近義複合' },
      { query: '~~你', mode: '0243', label: '近義複合，尾字同「你」同韻' },
      { query: '33~~你', mode: '0243', label: '33同音 + 近義複合 + 尾字同「你」同韻' },
    ],
  },
  {
    id: 'compound-ant',
    title: '反義複合詞',
    intro: '!! 搵二字反義複合；可加碼前綴或尾韻字。',
    examples: [
      { query: '!!', mode: '0243', label: '二字反義複合（如生死、是非）', familyId: 'compound_ant' },
      { query: '33!!', mode: '0243', label: '33同音 + 反義複合' },
      { query: '!!你', mode: '0243', label: '反義複合，尾字同「你」同韻' },
      { query: '33!!你', mode: '0243', label: '33同音 + 反義複合 + 尾字同「你」同韻' },
    ],
  },
  {
    id: 'doubled',
    title: '同音節疊字',
    intro: '$$ 搵二字詞且兩字音節相同（聲調不限）；語法鏡像 ~~。',
    examples: [
      { query: '$$', mode: '0243', label: '二字同音節疊字（如慢慢、識食）', familyId: 'compound_doubled' },
      { query: '33$$', mode: '0243', label: '33 同音 + 同音節疊字' },
      { query: '$$你', mode: '0243', label: '疊字，尾字同「你」同韻' },
    ],
  },
  {
    id: 'heteronym',
    title: '同音異讀',
    intro: '{左碼}/{右碼} 搵同一字面、至少兩個唔同讀音；? 通配碼位。',
    examples: [
      { query: '33/34', mode: '0243', label: '如「今晚」gam1 maan1 與 gam1 maan5', familyId: 'heteronym_code' },
      { query: '?3/?4', mode: '0243', label: '只約束第 2 字碼 3／4 嘅異讀' },
    ],
  },
  {
    id: 'connective',
    title: '連接詞複合詞',
    intro: '中格填詞連接詞（與、和、或…）嘅三字複合；~與~ 近義、!與! 反義。',
    examples: [
      { query: '!與!', mode: '0243', label: '反義連接詞複合（如生與死）', familyId: 'connective_compound' },
      { query: '~與~', mode: '0243', label: '近義連接詞複合' },
    ],
  },
];

export function allGuideExamples(): GuideExample[] {
  return GUIDE_SECTIONS.flatMap((section) => section.examples);
}

/** ponytail: coverage — `npx tsx client/scripts/pwa-guide-coverage-self-check.ts` */
export function guideCoverageSelfCheck(): void {
  const tagged = allGuideExamples().filter((ex) => ex.familyId);
  const seen = new Set(tagged.map((ex) => ex.familyId));
  const missing = GUIDE_FAMILY_IDS.filter((id) => !seen.has(id));
  if (missing.length) {
    throw new Error(`guideCoverageSelfCheck: missing families: ${missing.join(', ')}`);
  }
}
