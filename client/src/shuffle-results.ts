import type { QueryResult } from './db/query';

/** Fisher-Yates shuffle — port of frontend/search-workbench.mjs shuffleResults */
export function shuffleResults<T>(items: T[]): T[] {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function mergeShuffledResults(
  previous: QueryResult[],
  next: QueryResult[],
): QueryResult[] {
  if (next.length <= previous.length) {
    return next;
  }
  return [...previous, ...next.slice(previous.length)];
}

/** ponytail: runnable self-check */
export function shuffleLogicSelfCheck(): void {
  const a = [1, 2, 3, 4, 5];
  const b = shuffleResults(a);
  if (b.length !== a.length || new Set(b).size !== a.length) {
    throw new Error('shuffleLogicSelfCheck: permutation');
  }
  const prev = [{ word: 'a' }, { word: 'b' }] as QueryResult[];
  const grown = [...prev, { word: 'c' }] as QueryResult[];
  const merged = mergeShuffledResults(prev, grown);
  if (merged.length !== 3 || merged[2]?.word !== 'c') {
    throw new Error('shuffleLogicSelfCheck: merge');
  }
}
