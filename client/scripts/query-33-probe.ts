/** ponytail: probe query 33 — `npx tsx client/scripts/query-33-probe.ts` */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { searchPage, SEARCH_PAGE_SIZE } from '../src/db/query.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);

for (const limit of [50, 100, 200, 500, 1200]) {
  const t0 = performance.now();
  const page = await searchPage({ query: '33', mode: '0243', limit, offset: 0 });
  console.log(`limit=${limit} ms=${Math.round(performance.now() - t0)} total=${page.total} items=${page.items.length}`);
}

const full = await searchPage({ query: '33', mode: '0243', limit: SEARCH_PAGE_SIZE, offset: 0 });
console.log('default page literals:', full.items.slice(0, 5).map((r) => r.word).join(', '), '...');

await db.close();