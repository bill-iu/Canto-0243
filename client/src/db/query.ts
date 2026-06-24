/**
 * Query Engine for Canto-0243 PWA
 * Port of Python query logic to JavaScript
 * Interfaces with sql.js to execute queries against lyrics.db
 */

import { getDatabase, initializeDatabase, isDatabaseInitialized } from './init';
import { Database } from 'sql.js';

/**
 * Query options for search
 */
export interface QueryOptions {
  query: string;
  mode?: '0243' | '02493' | 'synonym';
  limit?: number;
  offset?: number;
}

/**
 * Query result structure
 */
export interface QueryResult {
  word: string;
  jyutping: string;
  code: string;
  definition?: string;
  score?: number;
}

/**
 * Execute a raw SQL query
 */
export async function executeSQL(sql: string, params: any[] = []): Promise<any[]> {
  // Ensure database is initialized
  if (!isDatabaseInitialized()) {
    await initializeDatabase();
  }
  
  const db = getDatabase();
  
  try {
    const stmt = db.prepare(sql);
    const result = stmt.getAsObject(params);
    stmt.free();
    return result ? [result] : [];
  } catch (error) {
    console.error('SQL execution error:', error);
    return [];
  }
}

/**
 * Execute a SQL query that returns multiple rows
 */
export async function executeSQLAll(sql: string, params: any[] = []): Promise<any[]> {
  if (!isDatabaseInitialized()) {
    await initializeDatabase();
  }
  
  const db = getDatabase();
  
  try {
    const stmt = db.prepare(sql);
    const results = [];
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

/**
 * Search words by 0243 code pattern
 */
export async function searchByCode(pattern: string, limit: number = 50): Promise<QueryResult[]> {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE code GLOB ? 
    LIMIT ?
  `;
  
  const results = await executeSQLAll(sql, [pattern, limit]);
  return results.map((row: any) => ({
    word: row.word,
    jyutping: row.jyutping,
    code: row.code,
    score: 0 // Placeholder for ranking
  }));
}

/**
 * Search words by jyutping pattern
 */
export async function searchByJyutping(pattern: string, limit: number = 50): Promise<QueryResult[]> {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE jyutping LIKE ?
    LIMIT ?
  `;
  
  const results = await executeSQLAll(sql, [`%${pattern}%`, limit]);
  return results.map((row: any) => ({
    word: row.word,
    jyutping: row.jyutping,
    code: row.code,
    score: 0
  }));
}

/**
 * Search words by Chinese text
 */
export async function searchByText(text: string, limit: number = 50): Promise<QueryResult[]> {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE word LIKE ?
    LIMIT ?
  `;
  
  const results = await executeSQLAll(sql, [`%${text}%`, limit]);
  return results.map((row: any) => ({
    word: row.word,
    jyutping: row.jyutping,
    code: row.code,
    score: 0
  }));
}

/**
 * Main search function that dispatches based on query pattern
 */
export async function search(options: QueryOptions): Promise<QueryResult[]> {
  const { query, mode = '0243', limit = 50, offset = 0 } = options;
  
  // Simple dispatch based on query pattern
  // This will be enhanced with proper 0243 parsing logic
  
  // Check if query is numeric (0243/02493 pattern)
  if (/^[\d=+?*_#%]+$/.test(query)) {
    return searchByCode(query.replace(/[+?*_#%]/g, '?'), limit);
  }
  
  // Check if query contains Chinese characters
  if (/[\u4e00-\u9fff]/.test(query)) {
    return searchByText(query, limit);
  }
  
  // Check if query looks like jyutping
  if (/^[a-z0-9\s]+$/.test(query.toLowerCase())) {
    return searchByJyutping(query, limit);
  }
  
  // Default: try text search
  return searchByText(query, limit);
}

/**
 * Get database statistics
 */
export async function getDatabaseStats(): Promise<{ wordCount: number; tableCount: number }> {
  const db = getDatabase();
  
  const wordCount = await executeSQL("SELECT COUNT(*) as count FROM words");
  const tables = await executeSQLAll("SELECT name FROM sqlite_master WHERE type='table'");
  
  return {
    wordCount: wordCount[0]?.count || 0,
    tableCount: tables.length
  };
}

/**
 * Get table schema for debugging
 */
export async function getTableSchema(tableName: string): Promise<any[]> {
  return executeSQLAll(`PRAGMA table_info(${tableName})`);
}

// Re-export database initialization
export { initializeDatabase, getDatabase, isDatabaseInitialized } from './init';
