/** ponytail: DB-1 self-check — needs tests/fixtures/lyrics.db */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { databaseBackendSelfCheck } from '../src/db/database-backend.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(fixture)) {
  throw new Error(`db-backend-self-check: missing ${fixture}`);
}

const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(fixture)));
databaseBackendSelfCheck(db);
db.close();
console.log('db-backend self-check ok');
