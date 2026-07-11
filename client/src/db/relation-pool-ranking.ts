/** 近反義池 ranking / merge — port of domain/relations/ranking.py (Phase C PR4). */
import type { RelationPoolItem } from './relation-pool-snapshot.ts';

export const RUNTIME_DERIVED_ANT_SOURCES = new Set(['ant_syn_mirror', 'ant_cilin_exanded']);

const QUERY_SYNONYM_PRIORITY: Record<string, string[]> = {
  快樂: ['開心', '愉快', '高興', '歡樂', '快活', '喜悅', '稱快'],
};

const QUERY_ANTONYM_PRIORITY: Record<string, string[]> = {
  快樂: ['悲傷', '傷心', '難過', '痛苦', '哀傷', '憂愁', '沮喪'],
};

const SOURCE_BASE_RANK: Record<string, number> = {
  manual: 0,
  manual_syn_cluster: 18,
  manual_ant_mirror: 20,
  cilin: 10,
  antisem: 10,
  guotong: 15,
  ant_cilin_exanded: 25,
  ant_syn_bridge: 28,
  cow: 20,
  current_static: 15,
  runtime_static: 80,
  static_thesaurus: 80,
  embedding_cosine: 60,
  word_relations: 50,
};
export function sourceRank(source: string | null | undefined): number {
  if (!source) {
    return 50;
  }
  for (const [key, rank] of Object.entries(SOURCE_BASE_RANK)) {
    if (source.includes(key)) {
      return rank;
    }
  }
  return 40;
}

export function finalScore(source: string | null | undefined, confidence: number | null, inDb: boolean): number {
  const rank = sourceRank(source);
  const conf = confidence ?? 0;
  const bonus = inDb ? 5 : -10;
  return rank + conf * 20 + bonus;
}
export function shouldIncludeSynonym(query: string, candidate: string): boolean {
  if (!candidate || candidate === query) {
    return false;
  }
  if (query.length >= 2 && candidate.length === 1) {
    return false;
  }
  return true;
}

export function morphemeCharsFromWordLists(...wordLists: string[][]): Set<string> {
  const out = new Set<string>();
  for (const words of wordLists) {
    for (const s of words) {
      if (s.length === 1) {
        out.add(s);
      }
    }
  }
  return out;
}

function preferredRank(query: string, char: string, table: Record<string, string[]>): number {
  const prefs = table[query] ?? [];
  const idx = prefs.indexOf(char);
  return idx >= 0 ? idx : 999;
}

function cilinGroupRank(item: RelationPoolItem): [number, string, number] {
  const codes = item.group_codes;
  if (!codes.length) {
    return [1, '', 0];
  }
  return [0, codes[codes.length - 1]!, -codes.length];
}

function coreSynBoost(query: string, char: string): number {
  if (char.length !== query.length) {
    return 1;
  }
  if (query.length >= 2 && /[心快意悅]$/.test(char)) {
    return 0;
  }
  return 1;
}

function coreAntBoost(query: string, char: string): number {
  if (char.length !== query.length) {
    return 1;
  }
  if (query.length >= 2 && /[傷悲苦痛愁慘過]$/.test(char)) {
    return 0;
  }
  return 1;
}

function relevanceKey(
  query: string,
  item: RelationPoolItem,
  morphemeChars: Set<string>,
  kind: 'syn' | 'ant',
): Array<string | number> {
  const char = item.char;
  const qLen = query.length;
  const cLen = char.length;
  const baseSort = item._sort ?? 99;

  if (qLen >= 2 && cLen === 1) {
    return [999, 999, 999, 999, 999, char];
  }

  const lengthTier = cLen === qLen ? 0 : cLen <= qLen + 2 ? 1 : 2;
  const lengthDelta = Math.abs(cLen - qLen);
  const overlap = [...char].filter((ch) => query.includes(ch)).length;
  const startsMorpheme = char.length > 0 && morphemeChars.has(char[0]!);
  const preferred =
    kind === 'syn'
      ? preferredRank(query, char, QUERY_SYNONYM_PRIORITY)
      : preferredRank(query, char, QUERY_ANTONYM_PRIORITY);
  const coreBoost = kind === 'syn' ? coreSynBoost(query, char) : coreAntBoost(query, char);

  const key: Array<string | number> = [lengthTier, preferred];
  if (kind === 'syn') {
    const [hasGroup, leaf, depth] = cilinGroupRank(item);
    key.push(hasGroup, leaf, depth);
  }
  key.push(coreBoost, lengthDelta, startsMorpheme ? 1 : 0, overlap, -baseSort, char);
  return key;
}

function compareKeys(a: Array<string | number>, b: Array<string | number>): number {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const av = a[i] ?? 0;
    const bv = b[i] ?? 0;
    if (av < bv) {
      return -1;
    }
    if (av > bv) {
      return 1;
    }
  }
  return 0;
}

export function mergeRelationPools(
  dbPool: RelationPoolItem[],
  staticPool: RelationPoolItem[],
): Map<string, RelationPoolItem> {
  const merged = new Map<string, RelationPoolItem>();
  for (const item of [...dbPool, ...staticPool]) {
    const ch = item.char;
    if (!ch) {
      continue;
    }
    const prev = merged.get(ch);
    if (!prev || (item._sort ?? 99) < (prev._sort ?? 99)) {
      merged.set(ch, item);
    }
  }
  return merged;
}

export function sortSynPool(
  query: string,
  pool: RelationPoolItem[],
  morphemeChars: Set<string>,
): RelationPoolItem[] {
  return pool
    .filter((i) => shouldIncludeSynonym(query, i.char))
    .sort((a, b) => compareKeys(relevanceKey(query, a, morphemeChars, 'syn'), relevanceKey(query, b, morphemeChars, 'syn')));
}

export function sortAntPool(
  query: string,
  pool: RelationPoolItem[],
  morphemeChars: Set<string>,
): RelationPoolItem[] {
  return pool
    .filter((i) => shouldIncludeSynonym(query, i.char))
    .sort((a, b) => compareKeys(relevanceKey(query, a, morphemeChars, 'ant'), relevanceKey(query, b, morphemeChars, 'ant')));
}
