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

/**
 * 窄屏結果格跨欄：≤4→1、5–6→2、7–8→3、≥9→4。
 * 字長用 grapheme（`[...literal].length`）。
 */
export function resultItemGridSpan(literal: string): number {
  const n = [...literal].length;
  if (n <= 4) return 1;
  if (n <= 6) return 2;
  if (n <= 8) return 3;
  return 4;
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

/** ponytail: same script as badge self-check */
export function resultItemGridSpanSelfCheck(): void {
  const cases: Array<[string, number]> = [
    ['', 1],
    ['好', 1],
    ['香港', 1],
    ['一二三四', 1],
    ['一二三四五', 2],
    ['一二三四五六', 2],
    ['一二三四五六七', 3],
    ['一二三四五六七八', 3],
    ['一二三四五六七八九', 4],
    ['一二三四五六七八九十十一', 4],
  ];
  for (const [literal, want] of cases) {
    const got = resultItemGridSpan(literal);
    if (got !== want) {
      throw new Error(`resultItemGridSpanSelfCheck: ${literal || '(empty)'} → ${got}, want ${want}`);
    }
  }
}
