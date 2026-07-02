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
import { getDatabase, initializeDatabase, isDatabaseInitialized } from './init';

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
}

/**
 * Legacy QueryOptions interface
 */
export interface QueryOptions {
  query: string;
  mode?: '0243' | '02493' | 'synonym';
  limit?: number;
  offset?: number;
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
    case 'synonym':
      return 'syn';
    default:
      return 'm1';
  }
}

/**
 * Search with legacy QueryOptions interface
 * This maintains backward compatibility with existing code
 */
export async function search(options: QueryOptions): Promise<QueryResult[]> {
  const mode = mapLegacyMode(options.mode);
  const results = await searchWords(
    options.query,
    undefined, // code
    undefined, // char
    mode,
    options.limit || 50,
    options.offset || 0
  );
  
  // Convert engine results to legacy format
  return results.map((r) => ({
    word: r.word,
    jyutping: r.jyutping,
    code: r.code,
    score: r.score,
  }));
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
    const stmt = db.prepare(sql);
    const results = [];
    
    if (params.length > 0) {
      stmt.bind(params);
    }
    
    while (stmt.step()) {
      results.push(stmt.getAsObject());
    }
    stmt.free();
    return results;
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
export async function validateOfflineReadiness(): Promise<void> {
  const results = await search({
    query: OFFLINE_READINESS_PROBE_QUERY,
    mode: '0243',
    limit: 1,
  });
  if (!results.length || !results[0]?.word) {
    throw new Error('離線就緒驗證失敗：基本查詢無結果');
  }
}

/**
 * Get database statistics
 */
export async function getDatabaseStats(): Promise<{ wordCount: number; tableCount: number }> {
  const db = getDatabase();
  
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
export async function searchByCode(pattern: string, limit: number = 50): Promise<QueryResult[]> {
  return search({ query: pattern, mode: '0243', limit });
}

/**
 * Search by jyutping pattern
 */
export async function searchByJyutping(pattern: string, limit: number = 50): Promise<QueryResult[]> {
  return search({ query: pattern, mode: '0243', limit });
}

/**
 * Search by Chinese text
 */
export async function searchByText(text: string, limit: number = 50): Promise<QueryResult[]> {
  return search({ query: text, mode: '0243', limit });
}

// Export database initialization
export { initializeDatabase, getDatabase, isDatabaseInitialized } from './init';
