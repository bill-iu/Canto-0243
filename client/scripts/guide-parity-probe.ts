/** Compare PWA engine vs expected — probe known PWA guide failures with explain. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { searchPage } from '../src/db/query.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { queryEngine } from '../src/db/query-engine.ts';

const FAILS = [
  '?困潦倒=',
  '+香??',
  '?+你?',

  '23+好',
  '2+好3',
  '+門0',
  '3+ngo4',
  '3$漢4',
  '23+o',
  '!苦悶',
] as const;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadRhymeLetterData(repoRoot);

const dbPath = path.join(repoRoot, 'lyrics.db');
resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);

for (const q of FAILS) {
  const explained = await queryEngine.explain({ q, mode: 'm1' });
  const page = await searchPage({ query: q, mode: '0243', limit: 5 });
  console.log(
    `${q}\tkind=${explained.kind}\titems=${page.items.length}\thint=${page.hint ?? ''}`,
  );
}

await db.close();