/**
 * Database initialization — gate (閘前) vs tail (ADR-0032)
 */

import type { DatabaseBackend } from './database-backend.ts';
import { resolveDbBackendMode, type DbBackendMode } from './db-backend-mode.ts';
import { ensureLexiconInOpfs } from './opfs-lexicon.ts';
import { opfsAvailable } from './opfs-storage.ts';
import {
  getLexiconCacheStatus,
  resolveLexiconBytes,
  type LexiconRestoreSource,
} from './lexicon-restore.ts';
import {
  loadLexiconTarget,
  publicAssetUrl,
  lexiconVersionFromEnv,
  type LexiconTarget,
} from './lexicon-manifest.ts';
import { openSqlJsDatabase } from './sqljs-backend.ts';
import { openOpfsVfsDatabase, prewarmOpfsVfsWorker, resetOpfsVfsWorker } from './opfs-vfs-backend.ts';
import { applyRuntimeDbPatches } from './db-patch.ts';
import { ensureGateAuxiliaryIndexes, resetGateAuxiliaryIndexes } from './auxiliary-indexes.ts';
import { initStaticSynIndex, initStaticAntIndex, initStaticCilinSynIndex } from './thesaurus.ts';
import { reportGatePhase } from './startup-progress.ts';
import { invalidatePhonemeIndex } from './position-match/phoneme-index.ts';
import { resetCompoundCaches } from './compound.ts';
import { invalidateRelationGraph } from './relation-graph.ts';
import { invalidateLexiconMembership } from './lexicon-membership.ts';
import { invalidateRelationPoolCache } from './relation-pool-projection.ts';


let db: DatabaseBackend | null = null;
let isInitialized = false;
let staticRelationLoaded = false;
let lexiconTargetPromise: Promise<LexiconTarget> | null = null;
let databaseInitPromise: Promise<DatabaseBackend> | null = null;
let lastLexiconRestoreSource: LexiconRestoreSource | null = null;
let activeDbBackendMode: DbBackendMode | null = null;

const SKIP_OPFS_VFS_SESSION_KEY = 'canto-skip-opfs-vfs';

let injectedDb: DatabaseBackend | null = null;

export function clearOpfsVfsSessionSkip(): void {
  try {
    sessionStorage.removeItem(SKIP_OPFS_VFS_SESSION_KEY);
  } catch {
    /* sessionStorage unavailable */
  }
}

function shouldSkipOpfsVfsThisSession(): boolean {
  try {
    return sessionStorage.getItem(SKIP_OPFS_VFS_SESSION_KEY) === '1';
  } catch {
    return false;
  }
}

function markOpfsVfsSessionSkip(): void {
  try {
    sessionStorage.setItem(SKIP_OPFS_VFS_SESSION_KEY, '1');
  } catch {
    /* sessionStorage unavailable */
  }
}

export function getActiveDbBackendMode(): DbBackendMode {
  return activeDbBackendMode ?? getDbBackendMode();
}

export function injectDatabaseForTests(candidate: DatabaseBackend | null): void {
  injectedDb = candidate;
  invalidatePhonemeIndex();
  invalidateRelationGraph();
  resetCompoundCaches();
  invalidateLexiconMembership();
  invalidateRelationPoolCache();
}

export { resolveDbBackendMode, type DbBackendMode } from './db-backend-mode.ts';
export {
  getLexiconCacheStatus,
  type LexiconCacheStatus,
  type LexiconRestoreSource,
} from './lexicon-restore.ts';
export type { LexiconTarget } from './lexicon-manifest.ts';

export function getDbBackendMode(): DbBackendMode {
  return resolveDbBackendMode();
}

export function getCurrentLexiconTarget(): Promise<LexiconTarget> {
  lexiconTargetPromise ??= loadLexiconTarget();
  return lexiconTargetPromise;
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

async function persistLexiconForOffline(version: string, bytes: Uint8Array): Promise<void> {
  if (!(await opfsAvailable()) || !bytes.byteLength) return;
  try {
    const ensured = await ensureLexiconInOpfs({
      version,
      expectedByteSize: bytes.byteLength,
      fetchBytes: async () => bytes,
    });
    console.log(
      ensured.fetched
        ? `Lexicon persisted to OPFS (${ensured.byteSize} bytes)`
        : `Lexicon already in OPFS (${ensured.byteSize} bytes)`,
    );
  } catch (error) {
    console.warn('Lexicon OPFS persist skipped:', error);
  }
}

async function verifyLexiconIntegrity(
  bytes: Uint8Array,
  target: LexiconTarget,
): Promise<void> {
  if (target.byteSize != null && bytes.byteLength !== target.byteSize) {
    const { purgeStaleLexiconCaches } = await import('./lexicon-restore.ts');
    await purgeStaleLexiconCaches(
      target,
      `size ${bytes.byteLength} != ${target.byteSize}`,
    );
    throw new Error(
      `Lexicon size mismatch: expected ${target.byteSize} bytes, got ${bytes.byteLength}`,
    );
  }
  if (target.sha256 && typeof crypto !== 'undefined' && crypto.subtle) {
    const hashBuf = await crypto.subtle.digest('SHA-256', bytes);
    const hex = Array.from(new Uint8Array(hashBuf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
    if (hex !== target.sha256) {
      const { purgeStaleLexiconCaches } = await import('./lexicon-restore.ts');
      await purgeStaleLexiconCaches(target, 'sha256 mismatch');
      throw new Error('Lexicon integrity check failed (sha256 mismatch)');
    }
  }
}

async function initializeSqlJsPath(target: LexiconTarget): Promise<DatabaseBackend> {
  const { bytes, source } = await resolveLexiconBytes(target);
  lastLexiconRestoreSource = source;
  console.log(`Lexicon restore (${source}) → sql.js`);
  await verifyLexiconIntegrity(bytes, target);
  await persistLexiconForOffline(target.version, bytes);
  return loadSqlJsFromBytes(bytes);
}

async function initializeOpfsLexicon(target: LexiconTarget): Promise<DatabaseBackend> {
  if (!(await opfsAvailable())) {
    throw new Error('OPFS VFS unavailable');
  }
  const opened = await openOpfsVfsDatabase({
    version: target.version,
    fetchUrl: target.fetchUrl,
    gzip: target.useGzip,
    progressTotal: target.fetchByteSize,
    expectedByteSize: target.byteSize,
  });
  lastLexiconRestoreSource = opened.fetched ? 'network' : 'opfs';
  console.log(
    opened.fetched
      ? `Lexicon streamed to OPFS VFS (${opened.byteSize} bytes)`
      : `Lexicon opened from OPFS VFS (${opened.byteSize} bytes)`,
  );
  return opened.db;
}

async function openLexiconDatabase(target: LexiconTarget): Promise<DatabaseBackend> {
  const preferred = getDbBackendMode();
  if (preferred !== 'opfs-vfs' || shouldSkipOpfsVfsThisSession()) {
    if (preferred === 'opfs-vfs' && shouldSkipOpfsVfsThisSession()) {
      console.log('Lexicon open: skipping opfs-vfs this session (sticky degrade)');
    }
    activeDbBackendMode = 'sqljs';
    return initializeSqlJsPath(target);
  }
  try {
    const opened = await initializeOpfsLexicon(target);
    activeDbBackendMode = 'opfs-vfs';
    return opened;
  } catch (error) {
    console.warn('OPFS VFS lexicon open failed, degrading to sql.js', error);
    markOpfsVfsSessionSkip();
    activeDbBackendMode = 'sqljs';
    return initializeSqlJsPath(target);
  }
}

export async function ensureStaticRelationIndexes(): Promise<void> {
  if (staticRelationLoaded) return;
  try {
    const [synRes, antRes, cilinRes] = await Promise.all([
      fetch(publicAssetUrl('static-syn-index.json')),
      fetch(publicAssetUrl('static-ant-index.json')),
      fetch(publicAssetUrl('static-cilin-syn-index.json')),
    ]);
    if (synRes.ok) initStaticSynIndex(await synRes.json());
    if (antRes.ok) initStaticAntIndex(await antRes.json());
    if (cilinRes.ok) initStaticCilinSynIndex(await cilinRes.json());
    staticRelationLoaded = true;
  } catch {
    /* ponytail: DB graph fallback */
  }
}

export function getDefaultDbUrl(): string {
  return publicAssetUrl('lyrics.db');
}

export { ensureLexiconInOpfs, lexiconOpfsFileName, readLexiconFromOpfs, removeLexiconFromOpfs } from './opfs-lexicon.ts';

export function getLastLexiconRestoreSource(): LexiconRestoreSource | null {
  return lastLexiconRestoreSource;
}

export async function isLexiconCachedForBackend(): Promise<boolean> {
  const target = await getCurrentLexiconTarget();
  return (await getLexiconCacheStatus(target)).any;
}

/** Gate-only init: open lexicon + patches. Tail via `startTailPreload()`. */
export async function initializeDatabase(dbPath?: string): Promise<DatabaseBackend> {
  if (injectedDb) return injectedDb;
  if (db && isInitialized) return db;
  if (databaseInitPromise) return databaseInitPromise;

  databaseInitPromise = (async () => {
    try {
      prewarmOpfsVfsWorker();
      reportGatePhase('download', 0);

      const target: LexiconTarget = dbPath
        ? {
            version: lexiconVersionFromEnv(),
            dbUrl: dbPath,
            fetchUrl: dbPath,
            useGzip: false,
          }
        : await getCurrentLexiconTarget();

      db = await openLexiconDatabase(target);
      reportGatePhase('open', 0.4);
      // C1 ADR-0038: refuse legacy JSON phoneme columns.
      // Close + reset worker *before* purge (OPFS lock), then re-open once from channel.
      {
        const {
          assertPhonemeStorageContract,
          phonemeStorageContractOk,
        } = await import('./phoneme-contract.ts');
        const { purgeStaleLexiconCaches } = await import('./lexicon-restore.ts');
        if (!(await phonemeStorageContractOk(db))) {
          try {
            await db.close();
          } catch {
            /* ignore */
          }
          db = null;
          resetOpfsVfsWorker();
          await purgeStaleLexiconCaches(target, 'phoneme storage contract');
          db = await openLexiconDatabase(target);
          await assertPhonemeStorageContract(db);
        }
      }
      await applyRuntimeDbPatches(db);
      // Lexicon identity may have changed (re-open after contract purge)
      invalidatePhonemeIndex();
      invalidateRelationGraph();
      resetCompoundCaches();
      invalidateLexiconMembership();
      invalidateRelationPoolCache();
      reportGatePhase('open', 0.6);
      await ensureGateAuxiliaryIndexes();
      reportGatePhase('open', 1);
      isInitialized = true;

      console.log(`Database initialized (${getActiveDbBackendMode()})`);
      return db;
    } catch (error) {
      databaseInitPromise = null;
      isInitialized = false;
      if (db) {
        void db.close();
        db = null;
      }
      console.error('Failed to initialize database:', error);
      const offline = typeof navigator !== 'undefined' && !navigator.onLine;
      const detail =
        error instanceof Error && error.message && !/無法載入詞庫/.test(error.message)
          ? `（${error.message}）`
          : '';
      throw new Error(
        offline
          ? '離線無法載入詞庫；請連網開啟一次，待顯示「離線就緒」後再試飛航模式'
          : `無法載入詞庫，請確認網路後重試${detail}`,
      );
    }
  })();

  return databaseInitPromise;
}

export function getDatabase(): DatabaseBackend {
  if (injectedDb) return injectedDb;
  if (!db) throw new Error('Database not initialized. Call initializeDatabase() first.');
  return db;
}

export function isDatabaseInitialized(): boolean {
  return injectedDb !== null || isInitialized;
}

export function resetDatabase(): void {
  injectedDb = null;
  isInitialized = false;
  staticRelationLoaded = false;
  resetGateAuxiliaryIndexes();
  invalidatePhonemeIndex();
  invalidateRelationGraph();
  resetCompoundCaches();
  invalidateLexiconMembership();
  invalidateRelationPoolCache();
  lexiconTargetPromise = null;
  databaseInitPromise = null;
  lastLexiconRestoreSource = null;
  activeDbBackendMode = null;
  resetOpfsVfsWorker();
  if (db) {
    void db.close();
    db = null;
  }
}

export { db };