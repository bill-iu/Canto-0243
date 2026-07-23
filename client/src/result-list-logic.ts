import type { QueryResult } from './db/query';
import { mergeResultsByLiteral, isListableWordRow } from '../../shared/entry-detail-core.mjs';

export type EntryPickReading = {
  jyutping?: string;
  code?: string;
};

export type EntryPickPayload = {
  literal: string;
  jyutping?: string;
  readings?: EntryPickReading[];
};

export function displayResults(results: QueryResult[]): QueryResult[] {
  const seen = new Set<string>();
  return results.filter((row) => {
    if (!isListableWordRow(row)) return false;
    const key = `${row.word}\0${row.jyutping ?? ''}\0${row.code ?? ''}`;
    if (!row.word || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function mergedResultCount(results: QueryResult[]): number {
  return mergeResultsByLiteral(displayResults(results)).length;
}

/** 「N個讀音」徽章：查詢字串含 `/`（同音異讀；PWA 跟即時輸入）。 */
export function resultsShowReadingBadge(query: string | null | undefined): boolean {
  return Boolean(query && query.includes('/'));
}

/** ponytail: `npx tsx client/scripts/result-list-badge-self-check.ts` */
export function resultListBadgeSelfCheck(): void {
  if (resultsShowReadingBadge('23') || resultsShowReadingBadge('好') || resultsShowReadingBadge('')) {
    throw new Error('resultListBadgeSelfCheck: non-slash query');
  }
  if (!resultsShowReadingBadge('33/34') || !resultsShowReadingBadge('??/??')) {
    throw new Error('resultListBadgeSelfCheck: slash query');
  }
  // boolean 與 `/` 字串等價：memo 邊界只訂閱 boolean，唔訂閱整段 input
  const live = '23/';
  if (resultsShowReadingBadge(live) !== live.includes('/')) {
    throw new Error('resultListBadgeSelfCheck: boolean parity');
  }
  if (resultsShowReadingBadge('232') !== false) {
    throw new Error('resultListBadgeSelfCheck: no-slash stays false for memo stability');
  }
}
