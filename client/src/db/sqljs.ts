/** sql.js CJS/ESM interop — single import site for Node parity + Vite browser */
import initSqlJs from 'sql.js';

export { initSqlJs };

export type { DatabaseBackend, DatabaseStatement, SqlBindParams } from './database-backend.ts';

export type SqlJsModule = Awaited<ReturnType<typeof initSqlJs>>;

/** DB-1: query code targets DatabaseBackend; today backed by sql.js */
export type { DatabaseBackend as Database } from './database-backend.ts';
