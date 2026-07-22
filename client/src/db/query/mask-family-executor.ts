/** Mask-family MatchSpec execution — mirror of _mask_family_search_result. */
import type { Database } from '../sqljs.ts';
import { sortWordRows } from '../ranking.ts';
import { getEqualsSpan } from '../position-match/spec.ts';
import { executeMatchSpec, filterMatchSpecRows } from '../position-match/engine.ts';
import { normalizeToMatchSpec } from '../position-match/match-spec-registry.ts';
import type { ParsedQuery, QueryMode, QueryResult, SearchResult } from '../query-types.ts';
import type { WordRow } from '../position-match/word-row.ts';
import { codePrefixedWholeWordEqualsEmptyHint } from './equals-empty-hint.ts';
import { rowToResult, sortMaskFamilyRows } from './result-map.ts';

function normalizeSearchMode(mode: QueryMode): 'm1' | 'm2' {
  if (mode === 'm2' || mode === '02493') {
    return 'm2';
  }
  return 'm1';
}

/**
 * MF-6 / Phase C1: mask_family only via MatchSpec → filter/execute → page.
 * C1.1: both dual_phoneme and normal paths expose total + windowed items.
 */
export async function executeMaskFamilySearchResult(
  parsed: ParsedQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
  code?: string,
  shouldCancel?: () => boolean,
): Promise<SearchResult> {
  const spec = normalizeToMatchSpec(parsed);
  if (!spec) {
    return { items: [] };
  }
  const searchMode = normalizeSearchMode(mode);
  const dbCtx = { db, mode: searchMode, code: code ?? null, shouldCancel };

  let ordered: Awaited<ReturnType<typeof filterMatchSpecRows>>;
  if (spec.extra?.dual_phoneme) {
    // Engine merges dual dimensions; pull a large window then page once for total.
    ordered = await executeMatchSpec(spec, {
      ...dbCtx,
      limit: Math.max(offset + limit, limit) + 10_000,
      offset: 0,
    });
  } else {
    const allRows = await filterMatchSpecRows(spec, dbCtx);
    const ranked = await sortMaskFamilyRows(spec, allRows, db, mode);
    ordered =
      spec.literal_priority || spec.compound_kind ? ranked : sortWordRows(ranked);
  }

  const total = (() => {
    const seen = new Set<string>();
    for (const row of ordered) {
      const c = String((row as WordRow).char ?? (row as { word?: string }).word ?? '');
      if (c) seen.add(c);
    }
    return seen.size;
  })();
  const items = ordered.slice(offset, offset + limit).map((row) => {
    if ((row as QueryResult).word != null && (row as WordRow).char == null) {
      return row as QueryResult;
    }
    return rowToResult(row as WordRow);
  });

  let hint: string | undefined;
  if (!items.length && getEqualsSpan(spec)) {
    const emptyHint = await codePrefixedWholeWordEqualsEmptyHint(spec, db);
    if (emptyHint) {
      hint = emptyHint;
    }
  }
  return { items, total, hint };
}
