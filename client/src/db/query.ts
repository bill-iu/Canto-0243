/**
 * Query API - Simplified interface for the PWA client
 * Uses the ported query engine from Python
 */

import type { 
  QueryMode,
  SearchResult,
  SearchContext,
  QueryKind,
} from './query-engine';
import { 
  queryEngine,
  searchWords,
  executeSearch,
  normalizeQuery,
  parseQuery,
  normalizeAndParse,
} from './query-engine';
import {
  getCurrentLexiconTarget,
  getDatabase,
  getActiveDbBackendMode,
  getLastLexiconRestoreSource,
  initializeDatabase,
  isDatabaseInitialized,
} from './init';
import { queryRows } from './database-backend.ts';
import { getLexiconCacheStatus } from './lexicon-restore.ts';
import { opfsAvailable } from './opfs-storage.ts';
import { DEFAULT_RELATION_POOL_PAGE_SIZE } from './relation-pool-snapshot.ts';

// Re-export the query engine types
export type { 
  QueryMode,
  SearchResult,
  SearchContext,
  QueryKind,
};
export { 
  normalizeQuery,
  parseQuery,
  normalizeAndParse,
  executeSearch,
  queryEngine,
  searchWords,
};

/**
 * Legacy QueryResult interface for backward compatibility
 */
export interface QueryResult {
  word: string;
  jyutping: string;
  code: string;
  definition?: string;
  score?: number;
  resultType?: 'code' | 'jyutping' | 'word';
  anchor_dimension?: 'initial' | 'final';
  relation?: 'syn' | 'ant' | 'semantic_related';
  in_db?: boolean;
  source?: string;
}

export interface SearchPageResult {
  items: QueryResult[];
  total?: number;
  hint?: string;
  effectiveMode?: QueryMode;
  lookupLayout?: boolean;
}

/** 擷取頁上限（load-more／續頁）；ADR-0034 / CONTEXT § 擷取頁 */
export const SEARCH_PAGE_SIZE = 800;
/** 0243 家族首屏擷取（offset=0） */
export const SEARCH_FIRST_PAGE_SIZE = 400;

/**
 * Legacy QueryOptions interface
 */
export interface QueryOptions {
  query: string;
  mode?: '0243' | '02493' | 'synonym' | '394052';
  limit?: number;
  offset?: number;
  fallback_0243_mode?: '0243' | '02493' | '394052';
  ui_lang?: 'zh' | 'en';
  /** Cooperative cancel (PWA); checked in engine hot paths */
  shouldCancel?: () => boolean;
}

export function searchPageSizeForMode(mode?: QueryOptions['mode']): number {
  return mode === 'synonym' ? DEFAULT_RELATION_POOL_PAGE_SIZE : SEARCH_PAGE_SIZE;
}

/** 首屏 400／續頁 800；近反義沿用池頁 */
export function searchLimitForOffset(mode: QueryOptions['mode'] | undefined, offset: number): number {
  if (mode === 'synonym') return DEFAULT_RELATION_POOL_PAGE_SIZE;
  return (offset || 0) <= 0 ? SEARCH_FIRST_PAGE_SIZE : SEARCH_PAGE_SIZE;
}

/**
 * Map legacy mode names to engine mode names
 */
function mapLegacyMode(mode?: string): QueryMode {
  switch (mode) {
    case '0243':
      return 'm1';
    case '02493':
      return 'm2';
    case '394052':
      return 'm3';
    case 'synonym':
      return 'syn';
    default:
      return 'm1';
  }
}

function mapEngineResult(r: SearchResult['items'][number]): QueryResult {
  return {
    word: r.word,
    jyutping: r.jyutping,
    code: r.code,
    score: r.score,
    resultType: r.resultType,
    anchor_dimension: r.anchor_dimension,
    relation: r.relation,
    in_db: r.in_db,
    source: r.source,
  };
}

/**
 * Search with pagination metadata (total, hint, lookup resultType).
 */
export async function searchPage(options: QueryOptions): Promise<SearchPageResult> {
  const mode = mapLegacyMode(options.mode);
  const fallback = options.fallback_0243_mode ? mapLegacyMode(options.fallback_0243_mode) : undefined;
  const offset = options.offset ?? 0;
  const limit = options.limit ?? searchLimitForOffset(options.mode, offset);
  const result = await queryEngine.execute({
    q: options.query,
    mode,
    limit,
    offset,
    fallback_0243_mode: fallback,
    ui_lang: options.ui_lang,
    shouldCancel: options.shouldCancel,
  });
  return {
    items: result.items.map(mapEngineResult),
    total: result.total,
    hint: result.hint,
    effectiveMode: result.effective_mode,
    lookupLayout: result.lookup_layout,
  };
}

/**
 * Search with legacy QueryOptions interface
 * This maintains backward compatibility with existing code
 */
export async function search(options: QueryOptions): Promise<QueryResult[]> {
  const page = await searchPage(options);
  return page.items;
}

/**
 * Execute raw SQL query - for advanced use cases
 */
export async function executeSQL(sql: string, params: any[] = []): Promise<any[]> {
  if (!isDatabaseInitialized()) {
    await initializeDatabase();
  }
  
  const db = getDatabase();

  try {
    return queryRows(db, sql, params);
  } catch (error) {
    console.error('SQL execution error:', error);
    return [];
  }
}

/** Golden parity probe query — must succeed for offline readiness (see ADR-0024 D-G2). */
export const OFFLINE_READINESS_PROBE_QUERY = '事業';

/**
 * Validate DB can run a minimal real query (not COUNT-only).
 */
async function waitForLexiconCache(
  target: Awaited<ReturnType<typeof getCurrentLexiconTarget>>,
  attempts = 8,
): Promise<Awaited<ReturnType<typeof getLexiconCacheStatus>>> {
  for (let i = 0; i < attempts; i++) {
    const cache = await getLexiconCacheStatus(target);
    if (cache.any) {
      return cache;
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  return getLexiconCacheStatus(target);
}

export async function validateOfflineReadiness(): Promise<void> {
  const results = await search({
    query: OFFLINE_READINESS_PROBE_QUERY,
    mode: '0243',
    limit: 10,
  });
  const hasProbeWord = results.some((r) => r.word === OFFLINE_READINESS_PROBE_QUERY);
  if (!results.length || !hasProbeWord) {
    throw new Error('離線就緒驗證失敗：基本查詢無結果');
  }

  const mode = getActiveDbBackendMode();
  const restoreSource = getLastLexiconRestoreSource();
  // ponytail: OPFS VFS / OPFS restore already proved local lexicon this session
  if (mode === 'opfs-vfs' || restoreSource === 'opfs') {
    return;
  }

  const target = await getCurrentLexiconTarget();
  const cache = await waitForLexiconCache(target);
  const hasOpfs = await opfsAvailable();
  // ponytail: iOS 飛航依賴 OPFS；僅 SW 命中不足以保證冷啟
  if (hasOpfs && !cache.opfs) {
    throw new Error('離線就緒驗證失敗：詞庫尚未寫入本機儲存，請稍候或重試');
  }
  if (!hasOpfs && !cache.any) {
    throw new Error('離線就緒驗證失敗：詞庫未快取至本機');
  }
}

/**
 * Get database statistics
 */
export async function getDatabaseStats(): Promise<{ wordCount: number; tableCount: number }> {
  const wordCountResult = await executeSQL("SELECT COUNT(*) as count FROM words");
  const tables = await executeSQL("SELECT name FROM sqlite_master WHERE type='table'");
  
  return {
    wordCount: wordCountResult[0]?.count || 0,
    tableCount: tables.length
  };
}

/**
 * Search by 0243 code pattern
 */
export async function searchByCode(pattern: string, limit: number = SEARCH_PAGE_SIZE): Promise<QueryResult[]> {
  return search({ query: pattern, mode: '0243', limit });
}

/**
 * Search by jyutping pattern
 */
export async function searchByJyutping(pattern: string, limit: number = SEARCH_PAGE_SIZE): Promise<QueryResult[]> {
  return search({ query: pattern, mode: '0243', limit });
}

/**
 * Search by Chinese text
 */
export async function searchByText(text: string, limit: number = SEARCH_PAGE_SIZE): Promise<QueryResult[]> {
  return search({ query: text, mode: '0243', limit });
}

// Export database initialization
export { initializeDatabase, getDatabase, isDatabaseInitialized } from './init';
