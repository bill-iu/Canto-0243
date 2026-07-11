import type { QueryResult } from './db/query';
import { mergeResultsByLiteral, isListableWordRow } from '../../frontend/entry-detail-core.mjs';

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
