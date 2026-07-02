/**
 * DB-0: wa-sqlite + OPFSCoopSyncVFS in a dedicated Worker (OPFS sync handles).
 */
import SQLiteESMFactory from '@journeyapps/wa-sqlite/dist/wa-sqlite.mjs';
import * as SQLite from '@journeyapps/wa-sqlite/src/sqlite-api.js';
import { OPFSCoopSyncVFS } from '@journeyapps/wa-sqlite/src/examples/OPFSCoopSyncVFS.js';
import { SQLITE_OPEN_CREATE, SQLITE_OPEN_READONLY, SQLITE_OPEN_READWRITE } from '@journeyapps/wa-sqlite/src/sqlite-constants.js';

const DB_FILE = 'lyrics-opfs.db';
const VFS_NAME = 'opfs-coop';
/** CoopSync creates journal/wal siblings — reset must drop all */
const DB_RELATED_SUFFIXES = ['', '-journal', '-wal'] as const;

type Sqlite3 = ReturnType<typeof SQLite.Factory>;

let sqlite3: Sqlite3 | null = null;

async function ensureSqlite(): Promise<Sqlite3> {
  if (sqlite3) {
    return sqlite3;
  }
  const module = await SQLiteESMFactory();
  const db = SQLite.Factory(module);
  const vfs = await OPFSCoopSyncVFS.create(VFS_NAME, module);
  db.vfs_register(vfs, true);
  sqlite3 = db;
  return db;
}

/** ponytail: sync size probe — upgrade path: share with DB-2 import guard */
async function opfsImportedDbBytes(): Promise<number> {
  const root = await navigator.storage.getDirectory();
  try {
    const handle = await root.getFileHandle(DB_FILE);
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

async function requireImportedDb(): Promise<void> {
  const bytes = await opfsImportedDbBytes();
  if (bytes <= 0) {
    throw new Error('OPFS 尚無詞庫，請先按 Import');
  }
}

async function importDbToOpfs(bytes: Uint8Array): Promise<void> {
  const db = await ensureSqlite();
  // ponytail: CoopSync jAccess only sees VFS-registered paths — create shell first, then overwrite bytes
  const createHandle = await db.open_v2(
    DB_FILE,
    SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE,
    VFS_NAME,
  );
  await db.close(createHandle);

  const root = await navigator.storage.getDirectory();
  const handle = await root.getFileHandle(DB_FILE, { create: true });
  const access = await handle.createSyncAccessHandle();
  try {
    access.truncate(0);
    access.write(bytes, { at: 0 });
    access.truncate(bytes.byteLength);
  } finally {
    access.close();
  }
}

async function resetOpfsDb(): Promise<void> {
  // ponytail: drop VFS accessiblePaths cache — else COUNT opens empty CREATE shell
  sqlite3 = null;
  const root = await navigator.storage.getDirectory();
  for (const suffix of DB_RELATED_SUFFIXES) {
    try {
      await root.removeEntry(DB_FILE + suffix);
    } catch {
      // missing entry is fine
    }
  }
}

async function countWords(): Promise<number> {
  await requireImportedDb();
  const db = await ensureSqlite();
  const handle = await db.open_v2(DB_FILE, SQLITE_OPEN_READONLY, VFS_NAME);
  try {
    let count = -1;
    await db.exec(handle, 'SELECT COUNT(*) FROM words;', (row) => {
      count = Number(row[0]);
    });
    if (count < 0) {
      throw new Error('COUNT(*) returned no row');
    }
    return count;
  } finally {
    await db.close(handle);
  }
}

export type WorkerRequest =
  | { type: 'import-and-count'; bytes: Uint8Array }
  | { type: 'count-only' }
  | { type: 'reset' };

export type WorkerResponse =
  | { type: 'ok'; count: number; importedBytes: number; vfs: string; dbFile: string }
  | { type: 'reset-ok' }
  | { type: 'error'; message: string };

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  try {
    const msg = event.data;
    if (msg.type === 'reset') {
      await resetOpfsDb();
      const res: WorkerResponse = { type: 'reset-ok' };
      self.postMessage(res);
      return;
    }
    if (msg.type === 'import-and-count') {
      await importDbToOpfs(msg.bytes);
      const count = await countWords();
      const res: WorkerResponse = {
        type: 'ok',
        count,
        importedBytes: msg.bytes.byteLength,
        vfs: VFS_NAME,
        dbFile: DB_FILE,
      };
      self.postMessage(res);
      return;
    }
    if (msg.type === 'count-only') {
      const count = await countWords();
      const res: WorkerResponse = {
        type: 'ok',
        count,
        importedBytes: 0,
        vfs: VFS_NAME,
        dbFile: DB_FILE,
      };
      self.postMessage(res);
      return;
    }
    throw new Error(`unknown request: ${(msg as WorkerRequest).type}`);
  } catch (e) {
    const res: WorkerResponse = {
      type: 'error',
      message: e instanceof Error ? e.message : String(e),
    };
    self.postMessage(res);
  }
};
