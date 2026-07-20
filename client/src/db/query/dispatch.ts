/** Dispatch + execute routes (port of query_dispatch).
 *  Search entry is QueryEngine.execute / engine.executeSearch only — no shadow executeSearch here.
 */
import type { Database } from '../sqljs.ts';
import { queryRows } from '../database-backend.ts';
import { getCodeVariants } from '../code-variants.ts';
import { sortQueryResults, sortWordRows } from '../ranking.ts';
import { executeHeteronymCodeSearch } from '../heteronym.ts';
import { relationLookupItems } from '../relation-pool/index.ts';
import type { RelationPoolItem } from '../relation-pool/index.ts';
import {
  expectedWordLength,
  matchesJyutpingQuery,
} from '../jyutping-match.ts';
import { getEqualsSpan } from '../position-match/spec.ts';
import { executeMatchSpec, filterMatchSpecRows } from '../position-match/engine.ts';
import { normalizeToMatchSpec } from '../position-match/match-spec-registry.ts';
import { QueryKind, RouteKind } from '../query-kind.ts';
import { routeKindFor } from '../query-kind-registry.ts';
import type {
  DigitCodeQuery,
  HeteronymCodeQuery,
  JyutpingFragmentQuery,
  ParsedQuery,
  QueryMode,
  QueryResult,
  RelationLookupQuery,
  SearchContext,
  SearchResult,
  WordLookupQuery,
} from '../query-types.ts';
import type { WordRow } from '../position-match/word-row.ts';
import { codePrefixedWholeWordEqualsEmptyHint } from './equals-empty-hint.ts';
import { rowToResult, sortMaskFamilyRows } from './result-map.ts';
import { buildLookupLayout, deduplicateWordRows } from './lookup-layout.ts';
import { composeTransientWordRows } from '../db-patch.ts';

// Query Execution
// ============================================================================

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

function normalizeSearchMode(mode: QueryMode): 'm1' | 'm2' {
  if (mode === 'm2' || mode === '02493') {
    return 'm2';
  }
  return 'm1';
}

async function executeDigitCodeQuery(
  parsed: DigitCodeQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): Promise<SearchResult> {
  const q = parsed.raw_q;
  const searchMode = normalizeSearchMode(mode);
  const variants = getCodeVariants(q, searchMode);
  const placeholders = variants.map(() => '?').join(', ');
  const len = q.length;

  const sql = `
    SELECT char, jyutping, code
    FROM words
    WHERE code IN (${placeholders})
      AND (
        length = ?
        OR ((length IS NULL OR length = 0) AND length(char) = ?)
      )
  `;

  const rows = await queryRows(db, sql, [...variants, len, len]) as WordRow[];

  const sorted = sortQueryResults(deduplicateWordRows(rows).map((row) => rowToResult(row)));
  return { items: sorted.slice(offset, offset + limit), total: sorted.length };
}

/**
 * Execute word lookup query
 */
async function executeWordLookup(
  parsed: WordLookupQuery,
  db: Database,
  _mode: QueryMode,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  let matches = (await queryRows(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
    [parsed.raw_q],
  )) as WordRow[];

  // 缺庫：記憶體音節拼接（唔寫庫）— 對齊 Portable compose_transient_words
  if (!matches.length && /[\u4e00-\u9fff]/.test(parsed.raw_q)) {
    matches = (await composeTransientWordRows(db, parsed.raw_q)) as WordRow[];
  }

  const built = await buildLookupLayout(parsed.raw_q, deduplicateWordRows(matches), db);
  return {
    items: built.slice(offset, offset + limit),
    total: built.length,
    lookup_layout: true,
  };
}

/**
 * Execute jyutping fragment query
 */
async function executeJyutpingFragment(
  parsed: JyutpingFragmentQuery,
  db: Database,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  const wordLen = expectedWordLength(parsed.raw_q);
  if (wordLen == null) {
    return { items: [] };
  }

  const sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
  `;
  const rows = (await queryRows(db, sql, [wordLen, wordLen])) as WordRow[];
  const matched = deduplicateWordRows(rows).filter((row) =>
    matchesJyutpingQuery(String(row.jyutping ?? ''), parsed.raw_q),
  );
  const sorted = sortQueryResults(matched.map((row) => rowToResult(row)));
  return { items: sorted.slice(offset, offset + limit), total: sorted.length };
}

/**
 * MF-6 / Phase C1: mask_family only via MatchSpec → filter/execute → page.
 * C1.1: both dual_phoneme and normal paths expose total + windowed items.
 */
async function executeMaskFamilySearchResult(
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

async function executeRelationLookup(
  parsed: RelationLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  const seed = parsed.word.trim();
  if (!seed) {
    return { items: [] };
  }

  const rows = await relationLookupItems(
    db,
    seed,
    parsed.relation_kind,
    mode,
    parsed.code_prefix,
    limit,
    offset,
  );

  return {
    items: rows.map(poolItemToResult),
  };
}

export function poolItemToResult(item: RelationPoolItem): QueryResult {
  return {
    word: item.char,
    jyutping: item.jyutping,
    code: item.code,
    score: item.score ?? 0,
    relation: item.relation,
    in_db: item.in_db,
    source: item.source,
  };
}

// ============================================================================
// Query Engine Class (from query_dispatch.py)
// ============================================================================

/**
 * Main Query Engine class
 * Provides high-level search interface
 */
