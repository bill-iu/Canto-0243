/** ponytail: MF-3 getCandidatesForLength smoke test (fixture db) */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { positionMatchSourcesSelfCheck } from '../src/db/position-match/sources.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(fixture)) {
  throw new Error(`position-match-sources-self-check: missing ${fixture}`);
}

const SQL = await initSqlJs();
const native = new SQL.Database(fs.readFileSync(fixture));
const db = createSqlJsBackend(native);
await positionMatchSourcesSelfCheck(db);
await db.close();

console.log('position-match sources self-check ok');
