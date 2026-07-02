/**
 * Database Initialization with sql.js and httpvfs
 * Handles loading lyrics.db as a static asset with chunked/streamed loading
 */

import type { DatabaseBackend } from './database-backend.ts';
import { openSqlJsDatabase } from './sqljs-backend.ts';
import { initRankingData } from './ranking.ts';
import { loadCompoundListsFromUrl } from './compound.ts';
import { initRhymeLetterIndex } from './rime-index.ts';
import { initStaticSynIndex, initStaticAntIndex, initStaticCilinSynIndex } from './thesaurus.ts';

// Database instance singleton
let db: DatabaseBackend | null = null;
let isInitialized = false;
let rankingLoaded = false;

/** ponytail: parity runner / node probe only — inject pre-loaded backend */
let injectedDb: DatabaseBackend | null = null;

export function injectDatabaseForTests(candidate: DatabaseBackend | null): void {
  injectedDb = candidate;
}

function defaultDbUrl(): string {
  const ver = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  return new URL(`lyrics.${ver}.db`, import.meta.env.BASE_URL).toString();
}

async function loadBrowserRankingIndex(): Promise<void> {
  if (rankingLoaded) {
    return;
  }
  try {
    const url = new URL('ranking-index.json', import.meta.env.BASE_URL).toString();
    const res = await fetch(url);
    if (res.ok) {
      initRankingData(await res.json());
    }
  } catch {
    // ponytail: empty ranking signals — localeCompare-tier fallback via compareSearchResults defaults
  }
  rankingLoaded = true;
}

async function loadBrowserRhymeLetterIndex(): Promise<void> {
  try {
    const url = new URL('rhyme-letter-index.json', import.meta.env.BASE_URL).toString();
    const res = await fetch(url);
    if (res.ok) {
      initRhymeLetterIndex(await res.json());
    }
  } catch {
    // ponytail: rhyme_letters falls back to empty options
  }
}

async function loadBrowserStaticSynIndex(): Promise<void> {
  try {
    const base = import.meta.env.BASE_URL;
    const [synRes, antRes, cilinRes] = await Promise.all([
      fetch(new URL('static-syn-index.json', base).toString()),
      fetch(new URL('static-ant-index.json', base).toString()),
      fetch(new URL('static-cilin-syn-index.json', base).toString()),
    ]);
    if (synRes.ok) {
      initStaticSynIndex(await synRes.json());
    }
    if (antRes.ok) {
      initStaticAntIndex(await antRes.json());
    }
    if (cilinRes.ok) {
      initStaticCilinSynIndex(await cilinRes.json());
    }
  } catch {
    // ponytail: compound/relation fall back to DB graph only
  }
}

async function loadBrowserCompoundLists(): Promise<void> {
  try {
    await loadCompoundListsFromUrl(import.meta.env.BASE_URL);
  } catch {
    // ponytail: compound curated lists optional until public/data/syn_ant present
  }
}

export function getDefaultDbUrl(): string {
  return defaultDbUrl();
}

/**
 * Initialize the SQL.js database with lyrics.db
 * Uses httpvfs for efficient chunked loading of large database files
 */
export async function initializeDatabase(dbPath: string = defaultDbUrl()): Promise<DatabaseBackend> {
  if (injectedDb) {
    return injectedDb;
  }
  if (db && isInitialized) {
    return db;
  }

  try {
    const response = await fetch(dbPath);
    if (!response.ok) {
      throw new Error(`Failed to fetch lexicon package (${response.status})`);
    }
    const arrayBuffer = await response.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);

    db = await openSqlJsDatabase(uint8Array, (file: string) => {
      if (file.endsWith('.wasm')) {
        return `https://sql.js.org/dist/${file}`;
      }
      return file;
    });
    
    // Mark as initialized
    isInitialized = true;

    await Promise.all([
      loadBrowserRankingIndex(),
      loadBrowserRhymeLetterIndex(),
      loadBrowserStaticSynIndex(),
      loadBrowserCompoundLists(),
    ]);
    
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
export function getDatabase(): DatabaseBackend {
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
