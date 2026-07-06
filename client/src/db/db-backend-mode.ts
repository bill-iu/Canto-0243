/**
 * DB-3/DB-5 init backend mode — ADR-0024
 */
export type DbBackendMode = 'sqljs' | 'opfs-vfs';

export function resolveDbBackendMode(
  env: { readonly VITE_DB_BACKEND?: string } = (import.meta as ImportMeta).env as {
    readonly VITE_DB_BACKEND?: string;
  },
): DbBackendMode {
  const raw = env.VITE_DB_BACKEND?.trim().toLowerCase();
  return raw === 'opfs' || raw === 'opfs-vfs' ? 'opfs-vfs' : 'sqljs';
}
