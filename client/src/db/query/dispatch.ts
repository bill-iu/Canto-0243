/** Dispatch + execute routes (port of query_dispatch). */
import type { Database } from '../sqljs.ts';
import { getDatabase, initializeDatabase, isDatabaseInitialized } from '../init.ts';
import { queryRows } from '../database-backend.ts';
import { getCodeVariants } from '../code-variants.ts';
import {
  codeMatchesPingZePattern,
  isPingZeSerialQuery,
  tryParsePingZeSerial,
} from '../ping-zak.ts';
import { sortQueryResults, sortWordRows, compareSearchResults, literalPriorityCompare } from '../ranking.ts';
import { searchCompoundTiers } from '../compound.ts';
import { executeHeteronymCodeSearch } from '../heteronym.ts';
import { relationLookupItems, relationPoolPage, type RelationPoolItem } from '../relation-pool.ts';
import { rhymeFinalsFromJyutping } from '../jyutping-codec.ts';
import {
  expectedWordLength,
  matchesJyutpingQuery,
} from '../jyutping-match.ts';
import {
  getEqualsSpan,
  type MatchSpec,
} from '../position-match/spec.ts';
import { compoundSearchSpecFromMatchSpec, getCandidatesForLength } from '../position-match/sources.ts';
import { executeMatchSpec, filterMatchSpecRows } from '../position-match/engine.ts';
import { normalizeToMatchSpec } from '../position-match/match-spec-registry.ts';
import { getWordText } from '../position-match/word-row.ts';
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
  UnmatchedQuery,
  WordLookupQuery,
} from '../query-types.ts';
import type { WordRow } from '../position-match/word-row.ts';
import {
  normalizeAndParse,
  normalizeQuery,
  CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT,
  codePrefixedWholeWordEqualsEmptyHint,
  rowToResult,
  sortMaskFamilyRows,
} from './parse.ts';

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

/** Port of word_serializer.deduplicate_words */
function deduplicateWordRows(rows: WordRow[]): WordRow[] {
  const seen = new Set<string>();
  const out: WordRow[] = [];
  for (const row of rows) {
    const c = String(row.char ?? '');
    if (!c || seen.has(c)) {
      continue;
    }
    seen.add(c);
    out.push(row);
  }
  return out;
}

function getWordSortCode(row: WordRow): string {
  const code = String(row.code ?? '').trim();
  if (code) {
    return code;
  }
  // ponytail: no jyutping→0243 derive yet
  return '';
}

/** Port of lookup_layout._collect_codes_and_jyuts */
function collectCodesAndJyuts(rows: WordRow[]): {
  codes: string[];
  codeToJyuts: Map<string, string[]>;
} {
  const codes: string[] = [];
  const seenCodes = new Set<string>();
  const codeToJyuts = new Map<string, string[]>();
  for (const row of rows) {
    const c = getWordSortCode(row);
    if (c && /^\d+$/.test(c) && !seenCodes.has(c)) {
      seenCodes.add(c);
      codes.push(c);
    }
    const j = String(row.jyutping ?? '').trim();
    if (c && j) {
      const list = codeToJyuts.get(c) ?? [];
      if (!list.includes(j)) {
        list.push(j);
      }
      codeToJyuts.set(c, list);
    }
  }
  codes.sort((a, b) => Number(a) - Number(b));
  return { codes, codeToJyuts };
}

function finalsJsonForCode(exactMatches: WordRow[], code: string): string | null {
  for (const row of exactMatches) {
    if (getWordSortCode(row) !== code) {
      continue;
    }
    const finalsRaw = row.finals;
    if (finalsRaw) {
      return typeof finalsRaw === 'string' ? finalsRaw : JSON.stringify(finalsRaw);
    }
  }
  return null;
}

async function loadCodeCandidates(db: Database, lenQ: number, codes: string[]): Promise<WordRow[]> {
  if (!codes.length) {
    return [];
  }
  const placeholders = codes.map(() => '?').join(',');
  const rows = await queryRows(
    db,
    `SELECT char, jyutping, code, initials, finals, length FROM words WHERE length = ? AND code IN (${placeholders}) ORDER BY char, jyutping`,
    [lenQ, ...codes],
  ) as WordRow[];
  return sortWordRows(rows);
}

function lookupLiteralChars(q: string): string[] {
  return [...new Set([...q])];
}

function wordSharesLookupLiteral(char: string, literals: string[]): boolean {
  return literals.some((ch) => char.includes(ch));
}

/** 漢字 lookup：同碼同韻含字面 → 同碼其他含字面 → 異碼含字面 */
async function appendLookupLiteralTiers(
  results: QueryResult[],
  seen: Set<string>,
  opts: {
    q: string;
    codes: string[];
    exactMatches: WordRow[];
    sameCodeCandidates: WordRow[];
    db: Database;
    lenQ: number;
  },
): Promise<void> {
  const literals = lookupLiteralChars(opts.q);
  if (!literals.length) {
    return;
  }
  const codeSet = new Set(opts.codes);

  for (const code of opts.codes) {
    const finJson = finalsJsonForCode(opts.exactMatches, code);
    if (!finJson) {
      continue;
    }
    const targetFinals = loadJsonList(finJson);
    const sameRhymeLiteral = opts.sameCodeCandidates.filter((row) => {
      if (getWordSortCode(row) !== code) {
        return false;
      }
      if (JSON.stringify(getRhymeFinals(row)) !== JSON.stringify(targetFinals)) {
        return false;
      }
      return wordSharesLookupLiteral(String(row.char ?? ''), literals);
    });
    appendLookupWords(results, seen, sortWordRows(sameRhymeLiteral));
  }

  const sameCodeLiteral = opts.sameCodeCandidates.filter((row) =>
    wordSharesLookupLiteral(String(row.char ?? ''), literals),
  );
  appendLookupWords(results, seen, sortWordRows(sameCodeLiteral));

  const [allLen] = await getCandidatesForLength(opts.db, opts.lenQ, { unlimited: true });
  const diffCodeLiteral = allLen.filter((row) => {
    const code = getWordSortCode(row);
    const ch = String(row.char ?? '');
    return code && !codeSet.has(code) && wordSharesLookupLiteral(ch, literals);
  });
  appendLookupWords(results, seen, sortWordRows(diffCodeLiteral));
}

async function resolveTailRhymeRefFromDb(
  db: Database,
  lastCh: string,
  lenQ: number,
): Promise<{ ref: string | null; pos: number }> {
  const refPos = lenQ > 0 ? Math.max(0, lenQ - 1) : 0;
  if (!lastCh) {
    return { ref: null, pos: refPos };
  }
  const row = await equalsAuthoritativeRow(db, lastCh);
  if (!row) {
    return { ref: null, pos: refPos };
  }
  const fins = getRhymeFinals(row);
  return { ref: fins[0] ?? null, pos: refPos };
}

function appendLookupWords(
  results: QueryResult[],
  seen: Set<string>,
  rows: WordRow[],
): void {
  for (const row of deduplicateWordRows(rows)) {
    const char = String(row.char ?? '');
    if (!char || seen.has(char)) {
      continue;
    }
    seen.add(char);
    results.push({ ...rowToResult(row), resultType: 'word' });
  }
}

function appendPerCodeRhymeSections(
  results: QueryResult[],
  seen: Set<string>,
  opts: {
    q: string;
    codes: string[];
    exactMatches: WordRow[];
    candidatesByCode: Map<string, WordRow[]>;
  },
): void {
  const qChars = [...new Set([...opts.q])];
  for (const code of opts.codes) {
    const finJson = finalsJsonForCode(opts.exactMatches, code);
    if (!finJson) {
      continue;
    }
    const targetFinals = loadJsonList(finJson);
    const pool = (opts.candidatesByCode.get(code) ?? [])
      .filter((row) => JSON.stringify(getRhymeFinals(row)) === JSON.stringify(targetFinals))
      .slice(0, 50);
    const sharedChars = new Set(
      pool
        .filter((row) => {
          const text = String(row.char ?? '');
          return qChars.some((ch) => text.includes(ch));
        })
        .map((row) => String(row.char ?? '')),
    );
    const pure = pool.filter((row) => !sharedChars.has(String(row.char ?? '')));
    appendLookupWords(results, seen, sortWordRows(pure).slice(0, 200));
  }
}

function appendTailRhymeSection(
  results: QueryResult[],
  seen: Set<string>,
  opts: {
    codes: string[];
    candidatesByCode: Map<string, WordRow[]>;
    refVal: string | null;
    refPos: number;
  },
): void {
  if (opts.refVal == null) {
    return;
  }
  for (const code of opts.codes) {
    const matched: WordRow[] = [];
    for (const row of (opts.candidatesByCode.get(code) ?? []).slice(0, 50)) {
      const wf = getRhymeFinals(row);
      if (wf.length > opts.refPos && wf[opts.refPos] === opts.refVal) {
        matched.push(row);
      }
    }
    appendLookupWords(results, seen, matched);
  }
}

/** Port of lookup_layout.build_lookup_layout — PWA 略過 code／jyutping 標題列（詞條行已內嵌；Portable 保留） */
export async function buildLookupLayout(
  q: string,
  exactMatches: WordRow[],
  db: Database | null,
): Promise<QueryResult[]> {
  if (!exactMatches.length) {
    return [];
  }
  const results: QueryResult[] = [];
  const seenWords = new Set<string>();
  const lenQ = [...q].length;
  const { codes } = collectCodesAndJyuts(exactMatches);

  appendLookupWords(results, seenWords, exactMatches);
  if (!db || !codes.length) {
    return results;
  }

  const codeSet = new Set(codes);
  const candidates = await loadCodeCandidates(db, lenQ, codes);
  const candidatesByCode = new Map<string, WordRow[]>();
  for (const row of candidates) {
    const code = getWordSortCode(row);
    if (!codeSet.has(code)) {
      continue;
    }
    const list = candidatesByCode.get(code) ?? [];
    list.push(row);
    candidatesByCode.set(code, list);
  }

  await appendLookupLiteralTiers(results, seenWords, {
    q,
    codes,
    exactMatches,
    sameCodeCandidates: candidates,
    db,
    lenQ,
  });

  appendPerCodeRhymeSections(results, seenWords, {
    q,
    codes,
    exactMatches,
    candidatesByCode,
  });

  const { ref, pos } = await resolveTailRhymeRefFromDb(db, q.slice(-1) ?? '', lenQ);
  appendTailRhymeSection(results, seenWords, {
    codes,
    candidatesByCode,
    refVal: ref,
    refPos: pos,
  });
  appendLookupWords(
    results,
    seenWords,
    sortWordRows(candidates.filter((row) => !seenWords.has(String(row.char ?? '')))),
  );
  return results;
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

type WordRow = Record<string, unknown>;

function loadJsonList(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map(String);
  }
  if (typeof raw === 'string' && raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  return [];
}

function getWordParts(row: WordRow, field: 'initials' | 'finals'): string[] {
  return loadJsonList(row[field]);
}

function getRhymeFinals(row: WordRow): string[] {
  const fromCol = getWordParts(row, 'finals');
  if (fromCol.length) {
    return fromCol;
  }
  const jyut = String(row.jyutping ?? '');
  return jyut ? rhymeFinalsFromJyutping(jyut) : [];
}

async function equalsAuthoritativeRow(db: Database, literal: string): Promise<WordRow | null> {
  return await queryFirst(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 1',
    [literal],
  ) as WordRow | null;
}

/** MF-6: port of query_dispatch._mask_family_search_result */
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
  let items: QueryResult[];
  let total: number | undefined;

  if (spec.extra?.dual_phoneme) {
    const rows = await executeMatchSpec(spec, { ...dbCtx, limit, offset });
    items = rows.map((row) => rowToResult(row));
  } else {
    // E3: rank on WordRow, map only the page window
    const allRows = await filterMatchSpecRows(spec, dbCtx);
    const ordered = await sortMaskFamilyRows(spec, allRows, db, mode);
    const finalSorted = (spec.literal_priority || spec.compound_kind)
      ? ordered
      : sortWordRows(ordered);
    total = finalSorted.length;
    items = finalSorted.slice(offset, offset + limit).map((row) => rowToResult(row));
  }

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
