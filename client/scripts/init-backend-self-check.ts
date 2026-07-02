/** ponytail: DB-3 — resolveDbBackendMode defaults */
import { resolveDbBackendMode } from '../src/db/db-backend-mode.ts';

if (resolveDbBackendMode({}) !== 'sqljs') {
  throw new Error('init-backend-self-check: default mode must be sqljs');
}
if (resolveDbBackendMode({ VITE_DB_BACKEND: 'opfs' }) !== 'opfs') {
  throw new Error('init-backend-self-check: opfs env');
}
if (resolveDbBackendMode({ VITE_DB_BACKEND: 'sqljs' }) !== 'sqljs') {
  throw new Error('init-backend-self-check: sqljs env');
}
console.log('init-backend self-check ok');
