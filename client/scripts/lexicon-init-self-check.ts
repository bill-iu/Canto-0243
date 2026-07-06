/** ponytail: lexicon init single-flight + validate guards */
import { getLastLexiconRestoreSource, resetDatabase } from '../src/db/init.ts';
import { resolveDbBackendMode } from '../src/db/db-backend-mode.ts';

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

console.log('lexicon-init-self-check: ok');