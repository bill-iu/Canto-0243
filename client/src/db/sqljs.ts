/** sql.js CJS/ESM interop — single import site for Node parity + Vite browser */
import initSqlJs from 'sql.js';

export { initSqlJs };

export type SqlJsModule = Awaited<ReturnType<typeof initSqlJs>>;
export type Database = InstanceType<SqlJsModule['Database']>;
