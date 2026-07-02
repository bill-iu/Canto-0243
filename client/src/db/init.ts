/**
 * Database Initialization with sql.js and httpvfs
 * Handles loading lyrics.db as a static asset with chunked/streamed loading
 */

import type { DatabaseBackend } from './database-backend.ts';
import { resolveDbBackendMode, type DbBackendMode } from './db-backend-mode.ts';
import {
  ensureLexiconInOpfs,
  lexiconOpfsFileName,
  readLexiconFromOpfs,
} from './opfs-lexicon.ts';
import { opfsFileSize } from './opfs-storage.ts';
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

export function getDbBackendMode(): DbBackendMode {
  return resolveDbBackendMode();
}

function lexiconVersion(): string {
  return (import.meta as ImportMeta).env?.VITE_LEXICON_VERSION || 'dev';
}

function defaultDbUrl(): string {
  return new URL(`lyrics.${lexiconVersion()}.db`, import.meta.env.BASE_URL).toString();
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

async function fetchLexiconBytes(dbPath: string): Promise<Uint8Array> {
  const response = await fetch(dbPath);
  if (!response.ok) {
    throw new Error(`Failed to fetch lexicon package (${response.status})`);
  }
  return new Uint8Array(await response.arrayBuffer());
}

async function initializeSqlJsFetch(dbPath: string): Promise<DatabaseBackend> {
  return loadSqlJsFromBytes(await fetchLexiconBytes(dbPath));
}

async function initializeOpfsLexicon(version: string, dbPath: string): Promise<DatabaseBackend> {
  const ensured = await ensureLexiconInOpfs({
    version,
    fetchBytes: () => fetchLexiconBytes(dbPath),
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

/** DB-3: OPFS hit = offline lexicon present without SW cache */
export async function isLexiconCachedForBackend(
  mode: DbBackendMode = getDbBackendMode(),
  version: string = lexiconVersion(),
): Promise<boolean> {
  if (mode === 'opfs') {
    return (await opfsFileSize(lexiconOpfsFileName(version))) > 0;
  }
  if (!('caches' in globalThis)) {
    return false;
  }
  try {
    const match = await caches.match(defaultDbUrl());
    return Boolean(match);
  } catch {
    return false;
  }
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
        : await initializeSqlJsFetch(dbPath);

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
