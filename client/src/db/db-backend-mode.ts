/**
 * DB-3 init backend mode — ADR-0024
 */
export type DbBackendMode = 'sqljs' | 'opfs';

export function resolveDbBackendMode(
  env: { VITE_DB_BACKEND?: string } = (import.meta as ImportMeta).env,
): DbBackendMode {
  const raw = env.VITE_DB_BACKEND?.trim().toLowerCase();
  return raw === 'opfs' ? 'opfs' : 'sqljs';
}
