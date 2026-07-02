/**
 * Search result ranking — port of app/domain/lexicon/ranking.py
 * ponytail: call initRankingData from ranking-loader.node.ts (parity / Node only)
 */

type WordRow = Record<string, unknown>;

const PRON_RANK_SORT: Record<string, number> = { 預設: 0, 常用: 1, 罕見: 2 };
const UNKNOWN_PRON_RANK = 99;

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
  return Boolean(text) && [...text].every((ch) => /\u4e00-\u9fff/.test(ch));
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

function curatedBoost(char: string): number {
  return curated.has((char || '').trim()) ? 1 : 0;
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

/** ponytail: runnable self-check — `npx tsx client/scripts/ranking-self-check.ts` */
export function rankingLogicSelfCheck(): void {
  initRankingData({
    essay: { 窮困潦倒: 100, 窮苦潦倒: 50, 窮酸潦倒: 10 },
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
}

export { PRON_RANK_SORT, UNKNOWN_PRON_RANK };
