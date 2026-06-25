/**
 * Canto-0243 Browser Query Engine
 * Port of Python query engine to JavaScript/TypeScript
 * 
 * This module implements the core query logic from the Python backend
 * to enable full client-side search functionality in the browser.
 */

import { getDatabase, initializeDatabase, isDatabaseInitialized } from './init';
import { Database } from 'sql.js';

// ============================================================================
// Query Types and Constants
// ============================================================================

/**
 * Query modes supported by the engine
 */
export type QueryMode = 'm1' | 'm2' | '0243' | '02493' | 'syn';

/**
 * Query kind enumeration - maps to Python QueryKind
 */
export enum QueryKind {
  RELATION_LOOKUP = 'relation_lookup',
  COMPOUND_ANT = 'compound_ant',
  COMPOUND_SYN = 'compound_syn',
  HYBRID_TAIL_EQUALS_ALIAS = 'hybrid_tail_equals_alias',
  EQUALS = 'equals',
  PLUS_ANCHOR = 'plus_anchor',
  WILDCARD_CODE_ANCHOR = 'wildcard_code_anchor',
  CODE_REF_MIDDLE_RHYME = 'code_ref_middle_rhyme',
  SERIAL_PHONEME = 'serial_phoneme',
  PREFIX_WILDCARD_EQUALS = 'prefix_wildcard_equals',
  PARTIAL_RHYME_MASK = 'partial_rhyme_mask',
  PARTIAL_INITIAL_MASK = 'partial_initial_mask',
  LITERAL_REF = 'literal_ref',
  RHYME_ANCHOR = 'rhyme_anchor',
  TRIPLE_RHYME_ANCHOR = 'triple_rhyme_anchor',
  JYUTPING_ANCHOR = 'jyutping_anchor',
  HYBRID_CODE = 'hybrid_code',
  MASK = 'mask',
  DIGIT_CODE = 'digit_code',
  WORD_LOOKUP = 'word_lookup',
  JYUTPING_FRAGMENT = 'jyutping_fragment',
  UNMATCHED = 'unmatched',
}

/**
 * Route kind for query dispatch
 */
export enum RouteKind {
  DIGIT = 'digit',
  MASK_FAMILY = 'mask_family',
  RELATION = 'relation',
  LOOKUP = 'lookup',
  UNMATCHED = 'unmatched',
  EMPTY = 'empty',
}

/**
 * Base parsed query interface
 */
export interface ParsedQuery {
  kind: QueryKind;
  raw_q: string;
}

/**
 * Digit code query (pure numeric codes)
 */
export interface DigitCodeQuery extends ParsedQuery {
  kind: QueryKind.DIGIT_CODE;
  raw_q: string;
}

/**
 * Word lookup query (Chinese characters)
 */
export interface WordLookupQuery extends ParsedQuery {
  kind: QueryKind.WORD_LOOKUP;
  raw_q: string;
}

/**
 * Jyutping fragment query
 */
export interface JyutpingFragmentQuery extends ParsedQuery {
  kind: QueryKind.JYUTPING_FRAGMENT;
  raw_q: string;
}

/**
 * Mask query (contains wildcards)
 */
export interface MaskQuery extends ParsedQuery {
  kind: QueryKind.MASK;
  raw_q: string;
}

/**
 * Relation lookup query (near-synonym or antonym)
 */
export interface RelationLookupQuery extends ParsedQuery {
  kind: QueryKind.RELATION_LOOKUP;
  raw_q: string;
  relation_kind: 'syn' | 'ant';
  word: string;
  code_prefix?: string;
}

/**
 * Unmatched query (invalid syntax)
 */
export interface UnmatchedQuery extends ParsedQuery {
  kind: QueryKind.UNMATCHED;
  raw_q: string;
  hint?: string;
}

/**
 * Query result structure
 */
export interface QueryResult {
  word: string;
  jyutping: string;
  code: string;
  definition?: string;
  score: number;
}

/**
 * Search context for query execution
 */
export interface SearchContext {
  q: string | null;
  code?: string;
  char?: string;
  mode: QueryMode;
  limit: number;
  offset: number;
  fallback_0243_mode?: QueryMode;
}

/**
 * Search result with metadata
 */
export interface SearchResult {
  items: QueryResult[];
  total?: number;
  hint?: string;
  cache_path?: string;
  effective_mode?: QueryMode;
}

// ============================================================================
// Query Kind Metadata (from query_kind_registry.py)
// ============================================================================

interface QueryKindMeta {
  route: RouteKind;
  match_spec: boolean;
}

const QUERY_KIND_META: Record<QueryKind, QueryKindMeta> = {
  [QueryKind.RELATION_LOOKUP]: { route: RouteKind.RELATION },
  [QueryKind.COMPOUND_SYN]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_ANT]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.HYBRID_TAIL_EQUALS_ALIAS]: { route: RouteKind.MASK_FAMILY },
  [QueryKind.EQUALS]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PREFIX_WILDCARD_EQUALS]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PARTIAL_RHYME_MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PARTIAL_INITIAL_MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.SERIAL_PHONEME]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PLUS_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.WILDCARD_CODE_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.CODE_REF_MIDDLE_RHYME]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.LITERAL_REF]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.RHYME_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.TRIPLE_RHYME_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.JYUTPING_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.HYBRID_CODE]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.DIGIT_CODE]: { route: RouteKind.DIGIT },
  [QueryKind.WORD_LOOKUP]: { route: RouteKind.LOOKUP },
  [QueryKind.JYUTPING_FRAGMENT]: { route: RouteKind.LOOKUP },
  [QueryKind.UNMATCHED]: { route: RouteKind.UNMATCHED },
};

const MASK_FAMILY_KINDS: Set<QueryKind> = new Set(
  Object.entries(QUERY_KIND_META)
    .filter(([_, m]) => m.route === RouteKind.MASK_FAMILY)
    .map(([k]) => k as QueryKind)
);

const MATCH_SPEC_KINDS: Set<QueryKind> = new Set(
  Object.entries(QUERY_KIND_META)
    .filter(([_, m]) => m.match_spec)
    .map(([k]) => k as QueryKind)
);

function routeKindFor(kind: QueryKind): RouteKind {
  return QUERY_KIND_META[kind]?.route || RouteKind.EMPTY;
}

function usesMatchSpec(kind: QueryKind): boolean {
  return MATCH_SPEC_KINDS.has(kind);
}

// ============================================================================
// Query Normalization and Parsing (from query_parse.py)
// ============================================================================

/**
 * Normalize query string:
 * - Strip whitespace
 * - Handle code tail normalization
 * - Full-width punctuation normalization
 */
export function normalizeQuery(q: string): string {
  if (!q) return q;
  
  // Strip whitespace
  let normalized = q.trim();
  
  // Convert full-width punctuation to half-width
  // Full-width: ！＠＃＄％＆＊（）＋－＝７８？、。
  // Half-width: !@#$%&*()+-=78?,.
  const fullToHalf: Record<string, string> = {
    '！': '!', '＠': '@', '＃': '#', '＄': '$', '％': '%',
    '＆': '&', '＊': '*', '（': '(', '）': ')', '＋': '+',
    '－': '-', '＝': '=', '７': '7', '８': '8', '？': '?',
    '、': ',', '。': '.',
  };
  
  normalized = normalized.replace(/[！＠＃＄％＆＊（）＋－＝７８？、。]/g, (match) => fullToHalf[match] || match);
  
  return normalized;
}

/**
 * Check if query is pure digits
 */
function isPureDigits(q: string): boolean {
  return /^\d+$/.test(q);
}

/**
 * Check if query contains Chinese characters
 */
function hasChineseChars(q: string): boolean {
  return /[\u4e00-\u9fff]/.test(q);
}

/**
 * Check if query looks like jyutping (contains letters)
 */
function hasJyutpingChars(q: string): boolean {
  return /[a-zA-Z]/.test(q);
}

/**
 * Parse query and classify into QueryKind
 */
export function parseQuery(q: string): ParsedQuery {
  const normalized = normalizeQuery(q);
  
  // Check for relation syntax (syn/ant queries)
  // This is a simplified version - full implementation in Python has complex patterns
  if (normalized.startsWith('~') || normalized.startsWith('！') || 
      normalized.startsWith('!') || normalized.startsWith('～')) {
    return {
      kind: QueryKind.RELATION_LOOKUP,
      raw_q: normalized,
      relation_kind: normalized.startsWith('~') || normalized.startsWith('～') ? 'syn' : 'ant',
      word: normalized.slice(1),
    } as RelationLookupQuery;
  }
  
  // Check for various mask patterns
  // This is a placeholder - full mask detection is complex
  if (looksLikeMaskQuery(normalized)) {
    return { kind: QueryKind.MASK, raw_q: normalized };
  }
  
  // Check for pure digit codes
  if (isPureDigits(normalized)) {
    return { kind: QueryKind.DIGIT_CODE, raw_q: normalized };
  }
  
  // Check for Chinese characters (word lookup)
  if (hasChineseChars(normalized)) {
    return { kind: QueryKind.WORD_LOOKUP, raw_q: normalized };
  }
  
  // Check for jyutping (contains letters)
  if (hasJyutpingChars(normalized)) {
    return { kind: QueryKind.JYUTPING_FRAGMENT, raw_q: normalized };
  }
  
  // Unmatched
  return { kind: QueryKind.UNMATCHED, raw_q: normalized, hint: '無法辨認的查詢語法' };
}

/**
 * Normalize and parse query
 */
export function normalizeAndParse(q: string): ParsedQuery {
  return parseQuery(normalizeQuery(q));
}

/**
 * Simple mask query detection
 */
function looksLikeMaskQuery(q: string): boolean {
  // Contains wildcards: ?, _, %, *
  return /[?*_%]/.test(q);
}

// ============================================================================
// Match Specification (from position_match/spec.py)
// ============================================================================

/**
 * Position match specification
 */
export interface MatchSpec {
  width: number; // Number of syllables/characters
  code_prefix?: string;
  // Additional spec properties would be added here
  // This is a simplified version
}

// ============================================================================
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
  return dispatch(parsed, { ...ctx, db });
}

/**
 * Execute list filter (when query is empty)
 */
function executeListFilter(db: Database, ctx: SearchContext): SearchResult {
  // Simple implementation: get all words
  // This should be enhanced with proper filtering
  const sql = `SELECT word, jyutping, code FROM words ORDER BY word LIMIT ? OFFSET ?`;
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0,
    });
  }
  stmt.free();
  
  return { items: results };
}

/**
 * Dispatch query based on parsed type
 */
function dispatch(parsed: ParsedQuery, ctx: SearchContext & { db: Database }): SearchResult {
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
      // For now, treat mask queries as simple text search
      return executeMaskFamily(parsed, db, mode, limit, offset);
    
    case RouteKind.RELATION:
      if (parsed.kind === QueryKind.RELATION_LOOKUP) {
        return executeRelationLookup(parsed as RelationLookupQuery, db, mode, limit, offset);
      }
      break;
    
    case RouteKind.UNMATCHED:
      if (parsed.kind === QueryKind.UNMATCHED) {
        const unmatched = parsed as UnmatchedQuery;
        return { items: [], hint: unmatched.hint };
      }
      break;
  }
  
  return { items: [] };
}

/**
 * Execute digit code query
 */
function executeDigitCodeQuery(
  parsed: DigitCodeQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  // Normalize mode: m1 = 0243 (loose), m2 = 02493 (strict)
  const normalizedMode = mode === 'm1' ? '0243' : mode === 'm2' ? '02493' : mode;
  
  // Simple implementation: match code exactly or with wildcards
  // In the full implementation, this would use proper 0243/02493 normalization
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE code GLOB ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  // For now, use simple GLOB matching
  // Full implementation would handle 0243 vs 02493 mode differences
  const pattern = parsed.raw_q.replace(/\*/g, '%').replace(/\?/g, '_');
  stmt.bind([pattern, limit, offset]);
  
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0,
    });
  }
  stmt.free();
  
  return { items: results };
}

/**
 * Execute word lookup query
 */
function executeWordLookup(
  parsed: WordLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE word LIKE ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([`%${parsed.raw_q}%`, limit, offset]);
  
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0,
    });
  }
  stmt.free();
  
  return { items: results };
}

/**
 * Execute jyutping fragment query
 */
function executeJyutpingFragment(
  parsed: JyutpingFragmentQuery,
  db: Database,
  limit: number,
  offset: number
): SearchResult {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE jyutping LIKE ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([`%${parsed.raw_q}%`, limit, offset]);
  
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0,
    });
  }
  stmt.free();
  
  return { items: results };
}

/**
 * Execute mask family query (contains wildcards)
 */
function executeMaskFamily(
  parsed: ParsedQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  // For now, treat as simple code matching
  // Full implementation would parse mask patterns properly
  const pattern = parsed.raw_q
    .replace(/\?/g, '_')  // ? matches single character
    .replace(/\*/g, '%')  // * matches any sequence
    .replace(/_%/g, '_');  // Clean up consecutive wildcards
  
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE code LIKE ? OR word LIKE ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([pattern, pattern, limit, offset]);
  
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0,
    });
  }
  stmt.free();
  
  return { items: results };
}

/**
 * Execute relation lookup query (synonym/antonym)
 */
function executeRelationLookup(
  parsed: RelationLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  // This is a placeholder - full implementation would use word_relations table
  // For now, just return empty results
  return {
    items: [],
    hint: '近反義模式功能正在開發中...',
  };
}

// ============================================================================
// Query Engine Class (from query_dispatch.py)
// ============================================================================

/**
 * Main Query Engine class
 * Provides high-level search interface
 */
export class QueryEngine {
  private db: Database | null = null;
  
  /**
   * Execute a search query
   */
  async execute(ctx: SearchContext): Promise<SearchResult> {
    // Initialize database if needed
    if (!isDatabaseInitialized()) {
      await initializeDatabase();
    }
    this.db = getDatabase();
    
    // If no database, return empty
    if (!this.db) {
      return { items: [], hint: '資料庫初始化失敗' };
    }
    
    // Add database to context
    const dbCtx = { ...ctx, db: this.db };
    
    // Handle empty query
    if (!ctx.q) {
      return executeListFilter(this.db, ctx);
    }
    
    // Normalize and parse
    const q = normalizeQuery(ctx.q);
    
    // Handle syn mode
    if (ctx.mode === 'syn') {
      return this.dispatchSynMode({ ...ctx, q }, dbCtx);
    }
    
    // Parse and dispatch
    const parsed = normalizeAndParse(ctx.q);
    return dispatch(parsed, dbCtx);
  }
  
  /**
   * Dispatch synonym mode queries
   */
  private dispatchSynMode(ctx: SearchContext & { q: string }, dbCtx: SearchContext & { db: Database }): SearchResult {
    // For now, treat syn mode like normal search but with relation queries
    // Full implementation would handle mode switching and relation lookup
    const parsed = normalizeAndParse(ctx.q);
    return dispatch(parsed, dbCtx);
  }
}

// Singleton engine instance
export const queryEngine = new QueryEngine();

// ============================================================================
// Public API
// ============================================================================

/**
 * Main search function - public entry point
 */
export async function searchWords(
  q: string | null = null,
  code?: string,
  char?: string,
  mode: QueryMode = '0243',
  limit: number = 100,
  offset: number = 0,
): Promise<QueryResult[]> {
  const result = await queryEngine.execute({
    q: q || undefined,
    code,
    char,
    mode,
    limit,
    offset,
  });
  return result.items;
}

// Export all types and functions
export type {
  QueryMode,
  QueryKind,
  RouteKind,
  ParsedQuery,
  QueryResult,
  SearchContext,
  SearchResult,
  DigitCodeQuery,
  WordLookupQuery,
  JyutpingFragmentQuery,
  MaskQuery,
  RelationLookupQuery,
  UnmatchedQuery,
  MatchSpec,
};
