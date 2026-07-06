/**
 * Database Initialization with sql.js and httpvfs
 * Handles loading lyrics.db as a static asset with chunked/streamed loading
 */

import type { DatabaseBackend } from './database-backend.ts';
import { resolveDbBackendMode, type DbBackendMode } from './db-backend-mode.ts';
import {
  ensureLexiconInOpfs,
} from './opfs-lexicon.ts';
import { opfsAvailable } from './opfs-storage.ts';
import {
  getLexiconCacheStatus,
  resolveLexiconBytes,
} from './lexicon-restore.ts';
import { openSqlJsDatabase } from './sqljs-backend.ts';
import { openOpfsVfsDatabase } from './opfs-vfs-backend.ts';
import { initRankingData } from './ranking.ts';
import { loadCompoundListsFromUrl } from './compound.ts';
import { applyRuntimeDbPatches } from './db-patch.ts';
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
    return publicAssetUrl('sql-wasm-browser.wasm');
  }
  return file;
}

async function loadSqlJsFromBytes(bytes: Uint8Array): Promise<DatabaseBackend> {
  return openSqlJsDatabase(bytes, sqlJsLocateFile);
}

/** sqljs 路徑：開庫後寫入 OPFS，供 iOS 飛航冷啟（SW 大檔快取不可靠） */
async function persistLexiconForOffline(version: string, bytes: Uint8Array): Promise<void> {
  if (!(await opfsAvailable()) || !bytes.byteLength) {
    return;
  }
  const ensured = await ensureLexiconInOpfs({
    version,
    fetchBytes: async () => bytes,
  });
  console.log(
    ensured.fetched
      ? `Lexicon persisted to OPFS (${ensured.byteSize} bytes)`
      : `Lexicon already in OPFS (${ensured.byteSize} bytes)`,
  );
}

async function initializeSqlJsPath(version: string, dbPath: string): Promise<DatabaseBackend> {
  const { bytes, source } = await resolveLexiconBytes(version, dbPath);
  console.log(`Lexicon restore (${source}) → sql.js`);
  await persistLexiconForOffline(version, bytes);
  return loadSqlJsFromBytes(bytes);
}

async function initializeOpfsLexicon(version: string, dbPath: string): Promise<DatabaseBackend> {
  if (!(await opfsAvailable())) {
    throw new Error('OPFS VFS unavailable');
  }
  const opened = await openOpfsVfsDatabase({ version, dbUrl: dbPath });
  console.log(
    opened.fetched
      ? `Lexicon streamed to OPFS VFS (${opened.byteSize} bytes)`
      : `Lexicon opened from OPFS VFS (${opened.byteSize} bytes)`,
  );
  return opened.db;
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
 * Initialize the database (sql.js default, or OPFS VFS when VITE_DB_BACKEND=opfs/opfs-vfs)
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
      mode === 'opfs-vfs'
        ? await initializeOpfsLexicon(version, dbPath)
        : await initializeSqlJsPath(version, dbPath);

    await applyRuntimeDbPatches(db);
    isInitialized = true;
    await loadAuxiliaryIndexes();

    console.log(`Database initialized (${mode})`);
    return db;
  } catch (error) {
    console.error('Failed to initialize database:', error);
    const offline = typeof navigator !== 'undefined' && !navigator.onLine;
    throw new Error(
      offline
        ? '離線無法載入詞庫；請連網開啟一次，待顯示「離線就緒」後再試飛航模式'
        : '無法載入詞庫，請確認網路後重試',
    );
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
    void db.close();
    db = null;
    isInitialized = false;
  }
}

// Export the database instance for direct use (after initialization)
export { db };
