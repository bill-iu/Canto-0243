/**
 * Database Initialization with sql.js and httpvfs
 * Handles loading lyrics.db as a static asset with chunked/streamed loading
 */

import { initSqlJs, type Database } from './sqljs.ts';

// Database instance singleton
let db: Database | null = null;
let isInitialized = false;

/** ponytail: parity runner / node probe only — inject pre-loaded sql.js Database */
let injectedDb: Database | null = null;

export function injectDatabaseForTests(candidate: Database | null): void {
  injectedDb = candidate;
}

function defaultDbUrl(): string {
  const ver = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  return new URL(`lyrics.${ver}.db`, import.meta.env.BASE_URL).toString();
}

export function getDefaultDbUrl(): string {
  return defaultDbUrl();
}

/**
 * Initialize the SQL.js database with lyrics.db
 * Uses httpvfs for efficient chunked loading of large database files
 */
export async function initializeDatabase(dbPath: string = defaultDbUrl()): Promise<Database> {
  if (injectedDb) {
    return injectedDb;
  }
  if (db && isInitialized) {
    return db;
  }

  try {
    // Initialize SQL.js
    const SQL = await initSqlJs({
      locateFile: (file: string) => {
        // For wasm file, use the imported version
        if (file.endsWith('.wasm')) {
          return `https://sql.js.org/dist/${file}`;
        }
        return file;
      }
    });

    // Fetch the whole DB once so SW cache stores a complete file.
    // This avoids iOS cache fragmentation with range/chunk requests.
    const response = await fetch(dbPath);
    if (!response.ok) {
      throw new Error(`Failed to fetch lexicon package (${response.status})`);
    }
    const arrayBuffer = await response.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);

    db = new SQL.Database(uint8Array);
    
    // Mark as initialized
    isInitialized = true;
    
    console.log('Database initialized successfully');
    return db;

  } catch (error) {
    console.error('Failed to initialize database:', error);
    throw new Error('Could not initialize database. Please ensure the lexicon package is accessible.');
  }
}

/**
 * Get the database instance
 * Throws if database is not initialized
 */
export function getDatabase(): Database {
  if (injectedDb) {
    return injectedDb;
  }
  if (!db) {
    throw new Error('Database not initialized. Call initializeDatabase() first.');
  }
  return db;
}

/**
 * Check if database is initialized
 */
export function isDatabaseInitialized(): boolean {
  return injectedDb !== null || isInitialized;
}

/**
 * Reset database instance (useful for testing)
 */
export function resetDatabase(): void {
  injectedDb = null;
  if (db) {
    db.close();
    db = null;
    isInitialized = false;
  }
}

// Export the database instance for direct use (after initialization)
export { db };
