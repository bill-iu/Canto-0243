/** Dispatch + execute routes (port of query_dispatch). */
import type { Database } from '../sqljs.ts';
import { getDatabase, initializeDatabase, isDatabaseInitialized } from '../init.ts';
import { queryRows } from '../database-backend.ts';
import { getCodeVariants } from '../code-variants.ts';
import {
  codeMatchesPingZePattern,
  isPingZeSerialQuery,
} from '../ping-zak.ts';
import { sortQueryResults, sortWordRows } from '../ranking.ts';
import { executeHeteronymCodeSearch } from '../heteronym.ts';
import { relationLookupItems, type RelationPoolItem } from '../relation-pool.ts';
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
  PingZeSerialQuery,
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
import {
  codePrefixedWholeWordEqualsEmptyHint,
  rowToResult,
  sortMaskFamilyRows,
} from './parse.ts';
import { buildLookupLayout, deduplicateWordRows } from './lookup-layout.ts';

// Query Execution
// ============================================================================

/**
 * Execute a search query using the SQL.js database
 */
export async function executeSearch(ctx: SearchContext): Promise<SearchResult> {
  // Ensure database is initialized
  if (!isDatabaseInitialized()) {
    await initializeDatabase();
  }
  
  const db = getDatabase();
  
  // Parse the query
  if (!ctx.q) {
    // Empty query - return all words with filters
    return executeListFilter(db, ctx);
  }
  
  const parsed = normalizeAndParse(ctx.q);
  return await dispatchParsed(parsed, { ...ctx, db });
}

/**
 * Execute list filter (when query is empty)
 */
export async function executeListFilter(db: Database, ctx: SearchContext): Promise<SearchResult> {
  const { limit, offset } = ctx;
  const sql = `SELECT char, jyutping, code FROM words ORDER BY char LIMIT ? OFFSET ?`;
  const results = (await queryRows(db, sql, [limit, offset])).map(rowToResult);

  return { items: results };
}

/**
 * Dispatch query based on parsed type
 */
export async function dispatchParsed(parsed: ParsedQuery, ctx: SearchContext & { db: Database }): Promise<SearchResult> {
  const routeKind = routeKindFor(parsed.kind);
  const { db, mode, limit, offset } = ctx;
  
  switch (routeKind) {
    case RouteKind.DIGIT:
      if (parsed.kind === QueryKind.PING_ZE_SERIAL) {
        return executePingZeSerialQuery(parsed as PingZeSerialQuery, db, limit, offset);
      }
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
        const items = await executeHeteronymCodeSearch(h, db, mode, limit, offset);
        return { items };
      }
      return { items: [] };
    
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

/**
 * Execute digit code query (pure digits only — P0 scope A)
 */
async function executePingZeSerialQuery(
  parsed: PingZeSerialQuery,
  db: Database,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  const pattern = parsed.raw_q;
  const len = pattern.length;
  const sql = `
    SELECT char, jyutping, code
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
  `;
  const rows = (await queryRows(db, sql, [len, len])) as WordRow[];
  const matched = deduplicateWordRows(rows).filter((row) =>
    codeMatchesPingZePattern(String(row.code ?? ''), pattern),
  );
  const sorted = sortQueryResults(matched.map((row) => rowToResult(row)));
  return { items: sorted.slice(offset, offset + limit), total: sorted.length };
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
  const matches = await queryRows(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
    [parsed.raw_q],
  );

  const built = await buildLookupLayout(parsed.raw_q, deduplicateWordRows(matches as WordRow[]), db);
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

  const total = ordered.length;
  const items = ordered.slice(offset, offset + limit).map((row) => rowToResult(row));

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
