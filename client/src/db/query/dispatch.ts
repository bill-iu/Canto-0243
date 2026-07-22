/** Thin dispatch — route switch only; executors hold implementation (P3#5).
 *  Search entry is QueryEngine.execute / engine.executeSearch only — no shadow executeSearch here.
 */
import type { Database } from '../sqljs.ts';
import { queryRows } from '../database-backend.ts';
import { executeHeteronymCodeSearch } from '../heteronym.ts';
import { QueryKind, RouteKind } from '../query-kind.ts';
import { routeKindFor } from '../query-kind-registry.ts';
import type {
  DigitCodeQuery,
  HeteronymCodeQuery,
  JyutpingFragmentQuery,
  ParsedQuery,
  RelationLookupQuery,
  SearchContext,
  SearchResult,
  UnmatchedQuery,
  WordLookupQuery,
} from '../query-types.ts';
import type { WordRow } from '../position-match/word-row.ts';
import { rowToResult } from './result-map.ts';
import { deduplicateWordRows } from './lookup-layout.ts';
import { executeMaskFamilySearchResult } from './mask-family-executor.ts';
import {
  executeRelationLookup,
  poolItemToResult,
} from './relation-syntax-executor.ts';
import {
  executeDigitCodeQuery,
  executeJyutpingFragment,
  executeWordLookup,
} from './word-lookup-executor.ts';

export { poolItemToResult };

/**
 * Execute list filter (when query is empty)
 */
export async function executeListFilter(db: Database, ctx: SearchContext): Promise<SearchResult> {
  const { limit, offset } = ctx;
  const sql = `SELECT char, jyutping, code FROM words ORDER BY char`;
  const all = deduplicateWordRows((await queryRows(db, sql, [])) as WordRow[]);
  const results = all.map(rowToResult);
  return { items: results.slice(offset, offset + limit), total: results.length };
}

/**
 * Dispatch query based on parsed type
 */
export async function dispatchParsed(parsed: ParsedQuery, ctx: SearchContext & { db: Database }): Promise<SearchResult> {
  const routeKind = routeKindFor(parsed.kind);
  const { db, mode, limit, offset } = ctx;

  switch (routeKind) {
    case RouteKind.DIGIT:
      if (parsed.kind === QueryKind.DIGIT_CODE) {
        return executeDigitCodeQuery(parsed as DigitCodeQuery, db, mode, limit, offset);
      }
      break;

    case RouteKind.LOOKUP:
      if (parsed.kind === QueryKind.WORD_LOOKUP) {
        return executeWordLookup(parsed as WordLookupQuery, db, mode, limit, offset);
      }
      if (parsed.kind === QueryKind.JYUTPING_FRAGMENT) {
        return executeJyutpingFragment(parsed as JyutpingFragmentQuery, db, limit, offset);
      }
      break;

    case RouteKind.MASK_FAMILY:
      return executeMaskFamilySearchResult(
        parsed,
        db,
        mode,
        limit,
        offset,
        ctx.code,
        ctx.shouldCancel,
      );

    case RouteKind.RELATION:
      if (parsed.kind === QueryKind.RELATION_LOOKUP) {
        return executeRelationLookup(parsed as RelationLookupQuery, db, mode, limit, offset);
      }
      break;

    case RouteKind.HETERONYM:
      if (parsed.kind === QueryKind.HETERONYM_CODE) {
        const h = parsed as HeteronymCodeQuery;
        const { items, total } = await executeHeteronymCodeSearch(h, db, mode, limit, offset);
        return { items, total };
      }
      return { items: [], total: 0 };

    case RouteKind.UNMATCHED:
      if (parsed.kind === QueryKind.UNMATCHED) {
        const unmatched = parsed as UnmatchedQuery;
        return { items: [], hint: unmatched.hint };
      }
      break;
  }

  return { items: [] };
}
