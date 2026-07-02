/**
 * Database Initialization with sql.js and httpvfs
 * Handles loading lyrics.db as a static asset with chunked/streamed loading
 */

import type { DatabaseBackend } from './database-backend.ts';
import { resolveDbBackendMode, type DbBackendMode } from './db-backend-mode.ts';
import {
  ensureLexiconInOpfs,
  readLexiconFromOpfs,
} from './opfs-lexicon.ts';
import {
  getLexiconCacheStatus,
  resolveLexiconBytes,
  type LexiconCacheStatus,
  type LexiconRestoreSource,
} from './lexicon-restore.ts';
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

export { resolveDbBackendMode, type DbBackendMode } from './db-backend-mode.ts';
export {
  getLexiconCacheStatus,
  type LexiconCacheStatus,
  type LexiconRestoreSource,
} from './lexicon-restore.ts';

export function getDbBackendMode(): DbBackendMode {
  return resolveDbBackendMode();
}

function lexiconVersion(): string {
  return (import.meta as ImportMeta).env?.VITE_LEXICON_VERSION || 'dev';
}

function publicAssetUrl(file: string): string {
  const base = import.meta.env.BASE_URL || '/';
  return `${base.replace(/\/?$/, '/')}${file.replace(/^\//, '')}`;
}

function defaultDbUrl(): string {
  return publicAssetUrl(`lyrics.${lexiconVersion()}.db`);
}

function sqlJsLocateFile(file: string): string {
  if (file.endsWith('.wasm')) {
    return `https://sql.js.org/dist/${file}`;
  }
  return file;
}

async function loadSqlJsFromBytes(bytes: Uint8Array): Promise<DatabaseBackend> {
  return openSqlJsDatabase(bytes, sqlJsLocateFile);
}

async function initializeSqlJsPath(version: string, dbPath: string): Promise<DatabaseBackend> {
  const { bytes, source } = await resolveLexiconBytes(version, dbPath);
  console.log(`Lexicon restore (${source}) → sql.js`);
  return loadSqlJsFromBytes(bytes);
}

async function initializeOpfsLexicon(version: string, dbPath: string): Promise<DatabaseBackend> {
  const ensured = await ensureLexiconInOpfs({
    version,
    fetchBytes: async () => (await resolveLexiconBytes(version, dbPath)).bytes,
  });
  const bytes = await readLexiconFromOpfs(version);
  if (!bytes?.byteLength) {
    throw new Error('OPFS lexicon missing after ensure');
  }
  console.log(
    ensured.fetched
      ? `Lexicon imported to OPFS (${ensured.byteSize} bytes)`
      : `Lexicon loaded from OPFS cache (${ensured.byteSize} bytes)`,
  );
  return loadSqlJsFromBytes(bytes);
}

async function loadBrowserRankingIndex(): Promise<void> {
  if (rankingLoaded) {
    return;
  }
  try {
    const url = publicAssetUrl('ranking-index.json');
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
    const url = publicAssetUrl('rhyme-letter-index.json');
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
    const [synRes, antRes, cilinRes] = await Promise.all([
      fetch(publicAssetUrl('static-syn-index.json')),
      fetch(publicAssetUrl('static-ant-index.json')),
      fetch(publicAssetUrl('static-cilin-syn-index.json')),
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

async function loadAuxiliaryIndexes(): Promise<void> {
  await Promise.all([
    loadBrowserRankingIndex(),
    loadBrowserRhymeLetterIndex(),
    loadBrowserStaticSynIndex(),
    loadBrowserCompoundLists(),
  ]);
}

export function getDefaultDbUrl(): string {
  return defaultDbUrl();
}

export { ensureLexiconInOpfs, lexiconOpfsFileName, readLexiconFromOpfs, removeLexiconFromOpfs } from './opfs-lexicon.ts';

/** DB-4: offline lexicon present in OPFS and/or SW cache */
export async function isLexiconCachedForBackend(
  _mode: DbBackendMode = getDbBackendMode(),
  version: string = lexiconVersion(),
  dbUrl: string = defaultDbUrl(),
): Promise<boolean> {
  return (await getLexiconCacheStatus(version, dbUrl)).any;
}

/**
 * Initialize the database (sql.js default, or OPFS-backed import when VITE_DB_BACKEND=opfs)
 */
export async function initializeDatabase(dbPath: string = defaultDbUrl()): Promise<DatabaseBackend> {
  if (injectedDb) {
    return injectedDb;
  }
  if (db && isInitialized) {
    return db;
  }

  try {
    const mode = getDbBackendMode();
    const version = lexiconVersion();
    db =
      mode === 'opfs'
        ? await initializeOpfsLexicon(version, dbPath)
        : await initializeSqlJsPath(version, dbPath);

    isInitialized = true;
    await loadAuxiliaryIndexes();

    console.log(`Database initialized (${mode})`);
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
