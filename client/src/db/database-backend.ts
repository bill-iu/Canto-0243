/**
 * DatabaseBackend — ADR-0024 DB-1
 * Minimal prepare/step surface used by query-engine and position-match.
 * ponytail: upgrade path = OPFS/wa-sqlite backend (DB-2+)
 */

export type SqlBindParams = Array<string | number | null | Uint8Array>;

export interface DatabaseStatement {
  bind(values?: SqlBindParams): void;
  step(): boolean;
  getAsObject(): Record<string, unknown>;
  free(): void;
}

export interface DatabaseBackend {
  prepare(sql: string): DatabaseStatement;
  close(): void;
}

/** ponytail: runnable self-check — npx tsx client/scripts/db-backend-self-check.ts */
export function databaseBackendSelfCheck(db: DatabaseBackend): void {
  const stmt = db.prepare('SELECT COUNT(*) AS n FROM words');
  stmt.bind([]);
  if (!stmt.step()) {
    stmt.free();
    throw new Error('databaseBackendSelfCheck: step returned false');
  }
  const row = stmt.getAsObject();
  stmt.free();
  const n = Number(row.n);
  if (!Number.isFinite(n) || n < 0) {
    throw new Error(`databaseBackendSelfCheck: bad count ${row.n}`);
  }
}
