/**
 * DatabaseBackend — ADR-0024 DB-1
 * Minimal prepare/step surface used by query-engine and position-match.
 * ponytail: upgrade path = OPFS/wa-sqlite backend (DB-2+)
 */

export type SqlBindParams = Array<string | number | null | Uint8Array>;

export interface DatabaseStatement {
  bind(values?: SqlBindParams): Promise<void>;
  step(): Promise<boolean>;
  getAsObject(): Promise<Record<string, unknown>>;
  reset(): Promise<void>;
  free(): Promise<void>;
}

export interface DatabaseBackend {
  prepare(sql: string): Promise<DatabaseStatement>;
  close(): Promise<void>;
}

/** ponytail: runnable self-check — npx tsx client/scripts/db-backend-self-check.ts */
export async function databaseBackendSelfCheck(db: DatabaseBackend): Promise<void> {
  const stmt = await db.prepare('SELECT COUNT(*) AS n FROM words');
  await stmt.bind([]);
  if (!(await stmt.step())) {
    await stmt.free();
    throw new Error('databaseBackendSelfCheck: step returned false');
  }
  const row = await stmt.getAsObject();
  await stmt.free();
  const n = Number(row.n);
  if (!Number.isFinite(n) || n < 0) {
    throw new Error(`databaseBackendSelfCheck: bad count ${row.n}`);
  }
}

export async function queryRows(
  db: DatabaseBackend,
  sql: string,
  params: SqlBindParams = [],
): Promise<Array<Record<string, unknown>>> {
  const stmt = await db.prepare(sql);
  try {
    await stmt.bind(params);
    const rows: Array<Record<string, unknown>> = [];
    while (await stmt.step()) {
      rows.push(await stmt.getAsObject());
    }
    return rows;
  } finally {
    await stmt.free();
  }
}

export async function queryFirst(
  db: DatabaseBackend,
  sql: string,
  params: SqlBindParams = [],
): Promise<Record<string, unknown> | null> {
  const stmt = await db.prepare(sql);
  try {
    await stmt.bind(params);
    return (await stmt.step()) ? await stmt.getAsObject() : null;
  } finally {
    await stmt.free();
  }
}

export async function runStatement(
  db: DatabaseBackend,
  sql: string,
  params: SqlBindParams = [],
): Promise<void> {
  const stmt = await db.prepare(sql);
  try {
    await stmt.bind(params);
    await stmt.step();
  } finally {
    await stmt.free();
  }
}
