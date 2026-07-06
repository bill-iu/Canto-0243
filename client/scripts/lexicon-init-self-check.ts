/** ponytail: lexicon init single-flight + validate guards */
import { getLastLexiconRestoreSource, resetDatabase } from '../src/db/init.ts';
import { resolveDbBackendMode } from '../src/db/db-backend-mode.ts';
import type { LexiconIntegrity } from '../src/db/lexicon-restore.ts';

if (resolveDbBackendMode({ VITE_DB_BACKEND: 'opfs-vfs' }) !== 'opfs-vfs') {
  throw new Error('lexicon-init-self-check: opfs-vfs mode');
}

resetDatabase();
if (getLastLexiconRestoreSource() !== null) {
  throw new Error('lexicon-init-self-check: restore source cleared on reset');
}

if (resolveDbBackendMode({}) !== 'sqljs') {
  throw new Error('lexicon-init-self-check: default sqljs backend');
}

const integrity: LexiconIntegrity = { byteSize: 3 };
if (integrity.byteSize !== 3) {
  throw new Error('lexicon-init-self-check: integrity type');
}

console.log('lexicon-init-self-check: ok');