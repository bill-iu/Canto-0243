/**
 * sql.js adapter — ADR-0024 DB-1
 */
import type { DatabaseBackend } from './database-backend.ts';
import { initSqlJs, type SqlJsModule } from './sqljs.ts';

export type SqlJsNativeDatabase = InstanceType<SqlJsModule['Database']>;

/** sql.js stays sync internally; the app-facing backend is async for OPFS VFS. */
export function createSqlJsBackend(native: SqlJsNativeDatabase): DatabaseBackend {
  return {
    async prepare(sql) {
      const stmt = native.prepare(sql);
      return {
        async bind(values = []) {
          stmt.bind(values);
        },
        async step() {
          return stmt.step();
        },
        async getAsObject() {
          return stmt.getAsObject();
        },
        async reset() {
          stmt.reset();
        },
        async free() {
          stmt.free();
        },
      };
    },
    async close() {
      native.close();
    },
  };
}

export async function openSqlJsDatabase(
  bytes: Uint8Array,
  locateFile?: (file: string) => string,
): Promise<DatabaseBackend> {
  const SQL = await initSqlJs(
    locateFile
      ? {
          locateFile,
        }
      : undefined,
  );
  return createSqlJsBackend(new SQL.Database(bytes));
}
