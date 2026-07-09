import SQLiteESMFactory from '@journeyapps/wa-sqlite/dist/wa-sqlite.mjs';
import * as SQLite from '@journeyapps/wa-sqlite';
import { OPFSCoopSyncVFS } from '@journeyapps/wa-sqlite/src/examples/OPFSCoopSyncVFS.js';

import type { SqlBindParams } from './database-backend.ts';
import { bodyStreamForLexiconFetch } from './lexicon-gunzip.ts';

const VFS_NAME = 'canto-opfs-coop';
const DB_RELATED_SUFFIXES = ['', '-journal', '-wal'] as const;

type Sqlite3 = ReturnType<typeof SQLite.Factory>;

export type OpfsVfsWorkerRequest =
  | { id: number; type: 'prewarm' }
  | {
      id: number;
      type: 'init';
      fileName: string;
      dbUrl: string;
      gzip?: boolean;
      progressTotal?: number;
      /** When set, existing OPFS file is dropped if size differs (stale channel cache). */
      expectedByteSize?: number;
    }
  | { id: number; type: 'query'; sql: string; params: SqlBindParams }
  | { id: number; type: 'close' };

export type OpfsVfsWorkerResponse =
  | { id: number; type: 'prewarm-ok' }
  | { id: number; type: 'init-ok'; fileName: string; byteSize: number; fetched: boolean }
  | { id: number; type: 'progress'; loaded: number; total: number }
  | { id: number; type: 'query-ok'; rows: Array<Record<string, unknown>> }
  | { id: number; type: 'close-ok' }
  | { id: number; type: 'error'; message: string };

let sqlite3: Sqlite3 | null = null;
let dbHandle: number | null = null;
let activeFileName = '';

function postProgress(loaded: number, total: number): void {
  self.postMessage({ id: 0, type: 'progress', loaded, total } satisfies OpfsVfsWorkerResponse);
}

async function ensureSqlite(): Promise<Sqlite3> {
  if (sqlite3) return sqlite3;
  const module = await SQLiteESMFactory();
  const db = SQLite.Factory(module);
  const vfs = await OPFSCoopSyncVFS.create(VFS_NAME, module);
  db.vfs_register(vfs, true);
  sqlite3 = db;
  return db;
}

async function opfsFileSize(fileName: string): Promise<number> {
  try {
    const root = await navigator.storage.getDirectory();
    const handle = await root.getFileHandle(fileName);
    const access = await handle.createSyncAccessHandle();
    try {
      return access.getSize();
    } finally {
      access.close();
    }
  } catch {
    return 0;
  }
}

async function removeRelatedFiles(fileName: string): Promise<void> {
  const root = await navigator.storage.getDirectory();
  for (const suffix of DB_RELATED_SUFFIXES) {
    try {
      await root.removeEntry(fileName + suffix);
    } catch {
      /* missing ok */
    }
  }
}

async function createVfsShell(db: Sqlite3, fileName: string): Promise<void> {
  const handle = await db.open_v2(
    fileName,
    SQLite.SQLITE_OPEN_READWRITE | SQLite.SQLITE_OPEN_CREATE,
    VFS_NAME,
  );
  await db.close(handle);
}

async function writeStreamToOpfs(
  fileName: string,
  body: ReadableStream<Uint8Array>,
  progressTotal?: number,
): Promise<number> {
  const root = await navigator.storage.getDirectory();
  const handle = await root.getFileHandle(fileName, { create: true });
  const access = await handle.createSyncAccessHandle();
  let offset = 0;
  let loaded = 0;
  const total = progressTotal && progressTotal > 0 ? progressTotal : 0;
  try {
    access.truncate(0);
    const reader = body.getReader();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      if (value?.byteLength) {
        access.write(value, { at: offset });
        offset += value.byteLength;
        loaded += value.byteLength;
        if (total > 0 || loaded % (512 * 1024) < value.byteLength) {
          postProgress(loaded, total || loaded);
        }
      }
    }
    access.truncate(offset);
    access.flush();
    postProgress(loaded, total || loaded);
    return offset;
  } finally {
    access.close();
  }
}

async function streamUrlIntoOpfs(
  fileName: string,
  dbUrl: string,
  gzip: boolean,
  progressTotal?: number,
): Promise<number> {
  const response = await fetch(dbUrl);
  if (!response.ok) {
    throw new Error(`Failed to fetch lexicon package (${response.status})`);
  }
  const total =
    progressTotal && progressTotal > 0
      ? progressTotal
      : Number(response.headers.get('Content-Length')) || 0;
  const input = bodyStreamForLexiconFetch(response, gzip);
  return writeStreamToOpfs(fileName, input, total);
}

async function ensureDbFile(
  fileName: string,
  dbUrl: string,
  gzip: boolean,
  progressTotal?: number,
  expectedByteSize?: number,
): Promise<{ byteSize: number; fetched: boolean }> {
  const existing = await opfsFileSize(fileName);
  if (existing > 0) {
    if (expectedByteSize == null || existing === expectedByteSize) {
      return { byteSize: existing, fetched: false };
    }
    // Same version key, different package (e.g. j2 compact slim vs legacy JSON).
    await removeRelatedFiles(fileName);
  }

  const db = await ensureSqlite();
  await removeRelatedFiles(fileName);
  await createVfsShell(db, fileName);
  const byteSize = await streamUrlIntoOpfs(fileName, dbUrl, gzip, progressTotal);
  if (byteSize <= 0) {
    throw new Error(`Empty lexicon payload for ${fileName}`);
  }
  if (expectedByteSize != null && byteSize !== expectedByteSize) {
    throw new Error(
      `Lexicon size mismatch after fetch: expected ${expectedByteSize}, got ${byteSize}`,
    );
  }
  return { byteSize, fetched: true };
}

async function ensureOpenDb(fileName = activeFileName): Promise<number> {
  if (dbHandle !== null && fileName === activeFileName) {
    return dbHandle;
  }
  await closeDb();
  const db = await ensureSqlite();
  dbHandle = await db.open_v2(fileName, SQLite.SQLITE_OPEN_READWRITE, VFS_NAME);
  activeFileName = fileName;
  return dbHandle;
}

async function closeDb(): Promise<void> {
  if (dbHandle === null || !sqlite3) return;
  const handle = dbHandle;
  dbHandle = null;
  await sqlite3.close(handle);
}

function normalizeValue(value: unknown): unknown {
  if (typeof value !== 'bigint') return value;
  const max = BigInt(Number.MAX_SAFE_INTEGER);
  const min = BigInt(Number.MIN_SAFE_INTEGER);
  return value <= max && value >= min ? Number(value) : value.toString();
}

async function query(sql: string, params: SqlBindParams): Promise<Array<Record<string, unknown>>> {
  const db = await ensureSqlite();
  const handle = await ensureOpenDb();
  const rows: Array<Record<string, unknown>> = [];

  for await (const stmt of db.statements(handle, sql)) {
    db.bind_collection(stmt, params);
    let columns: string[] | null = null;
    while ((await db.step(stmt)) === SQLite.SQLITE_ROW) {
      columns ??= db.column_names(stmt);
      const values = db.row(stmt);
      const row: Record<string, unknown> = {};
      for (let i = 0; i < columns.length; i += 1) {
        row[columns[i]!] = normalizeValue(values[i]);
      }
      rows.push(row);
    }
  }

  return rows;
}

self.onmessage = async (event: MessageEvent<OpfsVfsWorkerRequest>) => {
  const msg = event.data;
  try {
    if (msg.type === 'prewarm') {
      await ensureSqlite();
      self.postMessage({ id: msg.id, type: 'prewarm-ok' } satisfies OpfsVfsWorkerResponse);
      return;
    }
    if (msg.type === 'init') {
      const ensured = await ensureDbFile(
        msg.fileName,
        msg.dbUrl,
        Boolean(msg.gzip),
        msg.progressTotal,
        msg.expectedByteSize,
      );
      await ensureOpenDb(msg.fileName);
      self.postMessage({
        id: msg.id,
        type: 'init-ok',
        fileName: msg.fileName,
        byteSize: ensured.byteSize,
        fetched: ensured.fetched,
      } satisfies OpfsVfsWorkerResponse);
      return;
    }
    if (msg.type === 'query') {
      const rows = await query(msg.sql, msg.params);
      self.postMessage({ id: msg.id, type: 'query-ok', rows } satisfies OpfsVfsWorkerResponse);
      return;
    }
    if (msg.type === 'close') {
      await closeDb();
      self.postMessage({ id: msg.id, type: 'close-ok' } satisfies OpfsVfsWorkerResponse);
    }
  } catch (error) {
    self.postMessage({
      id: msg.id,
      type: 'error',
      message: error instanceof Error ? error.message : String(error),
    } satisfies OpfsVfsWorkerResponse);
  }
};