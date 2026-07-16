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

/** 「N個讀音」徽章：已送出查詢含 `/`（同音異讀）。 */
export function resultsShowReadingBadge(committedQuery: string | null | undefined): boolean {
  return Boolean(committedQuery && committedQuery.includes('/'));
}

/** ponytail: `npx tsx client/scripts/result-list-badge-self-check.ts` */
export function resultListBadgeSelfCheck(): void {
  if (resultsShowReadingBadge('23') || resultsShowReadingBadge('好') || resultsShowReadingBadge('')) {
    throw new Error('resultListBadgeSelfCheck: non-slash query');
  }
  if (!resultsShowReadingBadge('33/34') || !resultsShowReadingBadge('??/??')) {
    throw new Error('resultListBadgeSelfCheck: slash query');
  }
}
