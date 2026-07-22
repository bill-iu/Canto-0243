/**
 * Search result ranking — port of app/domain/lexicon/ranking.py
 * ponytail: call initRankingData from ranking-loader.node.ts (parity / Node only)
 */

type WordRow = Record<string, unknown>;

const PRON_RANK_SORT: Record<string, number> = { 預設: 0, 常用: 1, 罕見: 2, 棄用: 3 };
const UNKNOWN_PRON_RANK = 99;
const ANCHOR_EXCLUDED_PRON_RANKS = new Set([PRON_RANK_SORT['罕見'], PRON_RANK_SORT['棄用']]);

let essayFreq = new Map<string, number>();
let curated = new Set<string>();
let pronRankByCharJyut = new Map<string, number>();

export function initRankingData(data: {
  essay?: Record<string, number>;
  curated?: string[];
  pronRank?: Record<string, number>;
}): void {
  if (data.essay) {
    essayFreq = new Map(Object.entries(data.essay));
  }
  if (data.curated) {
    curated = new Set(data.curated);
  }
  if (data.pronRank) {
    pronRankByCharJyut = new Map(Object.entries(data.pronRank));
  }
}

function isPureHan(text: string): boolean {
  return Boolean(text) && [...text].every((ch) => /[\u4e00-\u9fff]/.test(ch));
}

function pronRankSortValue(char: string, jyutping: string): number {
  const c = char.trim();
  const j = jyutping.trim();
  if (!c || !j) {
    return UNKNOWN_PRON_RANK;
  }
  const key = `${c}\t${j}`;
  return pronRankByCharJyut.get(key) ?? UNKNOWN_PRON_RANK;
}

/** ADR-0051 §3: 錨點 union 剔罕見／棄用；未知仍入選 */
export function eligibleForAnchorPhonemeUnion(char: string, jyutping: string): boolean {
  return !ANCHOR_EXCLUDED_PRON_RANKS.has(pronRankSortValueForWord(char, jyutping));
}

export function pronRankSortValueForWord(char: string, jyutping: string): number {
  const text = (char || '').trim();
  const jyut = (jyutping || '').trim();
  if (!text || !jyut) {
    return UNKNOWN_PRON_RANK;
  }
  const syllables = jyut.split(/\s+/);
  if (text.length === 1) {
    return pronRankSortValue(text, jyut);
  }
  if (text.length !== syllables.length) {
    return UNKNOWN_PRON_RANK;
  }
  let max = 0;
  for (let i = 0; i < text.length; i++) {
    max = Math.max(max, pronRankSortValue(text[i]!, syllables[i]!));
  }
  return max;
}

function essayFrequency(char: string): number {
  return essayFreq.get((char || '').trim()) ?? 0;
}

export function getEssayFrequency(char: string): number {
  return essayFrequency(char);
}

/** Same pronunciation authority policy as app/domain/lexicon/ranking.py. */
export function compareAuthoritativeReadings(
  a: { char?: unknown; jyutping?: unknown },
  b: { char?: unknown; jyutping?: unknown },
): number {
  const aChar = String(a.char ?? '');
  const bChar = String(b.char ?? '');
  const aJyut = String(a.jyutping ?? '');
  const bJyut = String(b.jyutping ?? '');
  const aKey: Array<number | string> = [
    pronRankSortValueForWord(aChar, aJyut),
    -essayFrequency(aChar),
    aJyut.toLowerCase().includes('aa') ? 1 : 0,
    aJyut,
  ];
  const bKey: Array<number | string> = [
    pronRankSortValueForWord(bChar, bJyut),
    -essayFrequency(bChar),
    bJyut.toLowerCase().includes('aa') ? 1 : 0,
    bJyut,
  ];
  for (let index = 0; index < aKey.length; index += 1) {
    if (aKey[index]! < bKey[index]!) return -1;
    if (aKey[index]! > bKey[index]!) return 1;
  }
  return 0;
}

function curatedBoost(char: string): number {
  return curated.has((char || '').trim()) ? 1 : 0;
}

function getLiteralExactCount(row: WordRow, positions: Array<[number, string]>): number {
  const text = String(row.char ?? '');
  return positions.reduce((count, [pos, ch]) =>
    count + (pos < text.length && text[pos] === ch ? 1 : 0), 0);
}

export function literalPriorityCompare(
  a: WordRow, b: WordRow, positions: Array<[number, string]>
): number {
  const ea = getLiteralExactCount(a, positions);
  const eb = getLiteralExactCount(b, positions);
  if (ea !== eb) return eb - ea;  // higher exact count first (字面優先)
  return compareSearchResults(a, b);
}

export function searchResultSortKey(row: WordRow): [number, number, number, number, string, string] {
  const ch = String(row.char ?? '');
  const jyut = String(row.jyutping ?? '');
  const hanTier = isPureHan(ch) ? 0 : 1;
  return [
    hanTier,
    -essayFrequency(ch),
    -curatedBoost(ch),
    pronRankSortValueForWord(ch, jyut),
    ch,
    jyut,
  ];
}

export function compareSearchResults(a: WordRow, b: WordRow): number {
  const ka = searchResultSortKey(a);
  const kb = searchResultSortKey(b);
  for (let i = 0; i < ka.length; i++) {
    const av = ka[i]!;
    const bv = kb[i]!;
    if (av < bv) {
      return -1;
    }
    if (av > bv) {
      return 1;
    }
  }
  return 0;
}

export function sortWordRows(rows: WordRow[]): WordRow[] {
  return [...rows].sort(compareSearchResults);
}

export function sortQueryResults<T extends { word: string; jyutping: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) =>
    compareSearchResults(
      { char: a.word, jyutping: a.jyutping },
      { char: b.word, jyutping: b.jyutping },
    ),
  );
}

export function heteronymSortKey(row: WordRow): [number, number, number, string, string] {
  const ch = String(row.char ?? '');
  const jyut = String(row.jyutping ?? '');
  const hanTier = isPureHan(ch) ? 0 : 1;
  return [
    hanTier,
    -essayFrequency(ch),
    -curatedBoost(ch),
    ch,
    jyut,
  ];
}

export function compareHeteronym(a: WordRow, b: WordRow): number {
  const ka = heteronymSortKey(a);
  const kb = heteronymSortKey(b);
  for (let i = 0; i < ka.length; i++) {
    const av = ka[i]!;
    const bv = kb[i]!;
    if (av < bv) {
      return -1;
    }
    if (av > bv) {
      return 1;
    }
  }
  return 0;
}

export function sortHeteronymResults<T extends { word: string; jyutping: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) =>
    compareHeteronym(
      { char: a.word, jyutping: a.jyutping },
      { char: b.word, jyutping: b.jyutping },
    ),
  );
}

/** ponytail: runnable self-check — `npx tsx client/scripts/ranking-self-check.ts` */
export function rankingLogicSelfCheck(): void {
  initRankingData({
    essay: { 窮困潦倒: 100, 窮苦潦倒: 50, 窮酸潦倒: 10, '高頻': 100, '低頻': 10 },
    curated: ['窮困潦倒'],
    pronRank: {
      '窮\tkung4': 0,
      '困\tkwan3': 0,
      '苦\tsau4': 1,
      '酸\tsaan1': 2,
      '潦\tliu5': 0,
      '倒\tdou2': 0,
    },
  });
  const rows = sortQueryResults([
    { word: '窮酸潦倒', jyutping: 'kung4 saan1 liu5 dou2' },
    { word: '窮困潦倒', jyutping: 'kung4 kwan3 liu5 dou2' },
    { word: '窮苦潦倒', jyutping: 'kung4 sau4 liu5 dou2' },
  ]);
  const order = rows.map((r) => r.word).join(',');
  if (order !== '窮困潦倒,窮苦潦倒,窮酸潦倒') {
    throw new Error(`rankingLogicSelfCheck: got ${order}`);
  }

  // literal priority (缺字查詢字面優先) test — 門0 style
  const litPositions: Array<[number, string]> = [[0, '窮']];
  const litA = { char: '窮困潦倒', jyutping: 'kung4 kwan3 liu5 dou2' };
  const litB = { char: '困窮潦倒', jyutping: 'kwan3 kung4 liu5 dou2' };
  if (literalPriorityCompare(litA, litB, litPositions) >= 0) {
    throw new Error('literalPriorityCompare: 窮 at pos0 should precede');
  }

  // heteronym_sort_key test: freq primary, lexical jyut within char (no pron)
  const h1 = { char: '高頻', jyutping: 'gou1 pan4' };
  const h2 = { char: '低頻', jyutping: 'dai1 pan4' };
  const h3 = { char: '高頻', jyutping: 'gou2 pan4' };
  const hSorted = [h2, h1, h3].sort((a, b) => compareHeteronym(a, b));
  const hOrder = hSorted.map((r) => r.char).join(',');
  if (hOrder !== '高頻,高頻,低頻') {
    throw new Error(`heteronymSortKey char order: ${hOrder}`);
  }
  const hWithin = hSorted
    .filter((r) => r.char === '高頻')
    .map((r) => r.jyutping)
    .join(',');
  if (hWithin !== 'gou1 pan4,gou2 pan4') {
    throw new Error(`heteronymSortKey within jyut: ${hWithin}`);
  }
}

/** ponytail: runnable self-check — `npx tsx client/scripts/anchor-phoneme-options-self-check.ts` */
export function anchorPhonemeUnionEligibilitySelfCheck(): void {
  initRankingData({
    pronRank: {
      '難\tnaan4': 0,
      '難\tno4': 2,
      '潦\tliu2': 0,
      '潦\tlou5': 1,
      '信\tseon3': 0,
      '信\tsan1': 3,
    },
  });
  if (!eligibleForAnchorPhonemeUnion('難', 'naan4')) {
    throw new Error('anchorPhonemeUnionEligibilitySelfCheck: naan4 should be eligible');
  }
  if (eligibleForAnchorPhonemeUnion('難', 'no4')) {
    throw new Error('anchorPhonemeUnionEligibilitySelfCheck: no4 should be excluded');
  }
  if (!eligibleForAnchorPhonemeUnion('潦', 'lou5')) {
    throw new Error('anchorPhonemeUnionEligibilitySelfCheck: lou5 should be eligible');
  }
  if (!eligibleForAnchorPhonemeUnion('測', 'mak6')) {
    throw new Error('anchorPhonemeUnionEligibilitySelfCheck: unknown rank should be eligible');
  }
  if (!eligibleForAnchorPhonemeUnion('信', 'seon3')) {
    throw new Error('anchorPhonemeUnionEligibilitySelfCheck: seon3 should be eligible');
  }
  if (eligibleForAnchorPhonemeUnion('信', 'san1')) {
    throw new Error('anchorPhonemeUnionEligibilitySelfCheck: deprecated san1 should be excluded');
  }
}

export { PRON_RANK_SORT, UNKNOWN_PRON_RANK };
