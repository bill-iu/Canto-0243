/** Mask-family MatchSpec execution — mirror of _mask_family_search_result. */
import type { Database } from '../sqljs.ts';
import { sortWordRows } from '../ranking.ts';
import { executeCanonicalMatchSpecPage, filterMatchSpecRows } from '../position-match/engine.ts';
import { compileParsedQuery } from '../position-match/compiler.ts';
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
  const canonical = compileParsedQuery(parsed);
  if (canonical.phoneme_alternatives) {
    const page = await executeCanonicalMatchSpecPage(canonical, {
      db,
      mode: normalizeSearchMode(mode),
      limit,
      offset,
      code: code ?? null,
      shouldCancel,
    });
    return {
      items: page.rows.map((row) => rowToResult(row)),
      total: page.total,
    };
  }
  const searchMode = normalizeSearchMode(mode);
  const dbCtx = { db, mode: searchMode, code: code ?? null, shouldCancel };

  let ordered: Awaited<ReturnType<typeof filterMatchSpecRows>>;
  if (canonical.phoneme_alternatives) {
    // Engine merges dual dimensions; pull a large window then page once for total.
    ordered = (await executeCanonicalMatchSpecPage(canonical, {
      ...dbCtx,
      limit: Math.max(offset + limit, limit) + 10_000,
      offset: 0,
    })).rows;
  } else {
    const allRows = await filterMatchSpecRows(canonical, dbCtx);
    const ranked = await sortMaskFamilyRows(canonical, allRows, db, mode);
    ordered =
      canonical.ranking === 'literal_priority' || canonical.compound ? ranked : sortWordRows(ranked);
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
    if ((row as unknown as QueryResult).word != null && (row as unknown as WordRow).char == null) {
      return row as unknown as QueryResult;
    }
    return rowToResult(row as WordRow);
  });

  let hint: string | undefined;
  if (!items.length && canonical.equals_span) {
    const emptyHint = await codePrefixedWholeWordEqualsEmptyHint(canonical, db);
    if (emptyHint) {
      hint = emptyHint;
    }
  }
  return { items, total, hint };
}
