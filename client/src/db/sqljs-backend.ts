/**
 * sql.js adapter — ADR-0024 DB-1
 */
import type { DatabaseBackend } from './database-backend.ts';
import { initSqlJs, type SqlJsModule } from './sqljs.ts';

export type SqlJsNativeDatabase = InstanceType<SqlJsModule['Database']>;

/** sql.js already implements prepare/step; explicit adapter for DB-2 swap */
export function createSqlJsBackend(native: SqlJsNativeDatabase): DatabaseBackend {
  return native;
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
