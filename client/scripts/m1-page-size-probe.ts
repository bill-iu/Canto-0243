/** ponytail: 0243搜尋模式 page-size probe — `npx tsx client/scripts/m1-page-size-probe.ts` */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { searchPage } from '../src/db/query.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');

/** Representative 0243搜尋 queries: digit, wildcard, lookup, rhyme anchor */
const queries = [
  { q: '23', label: 'digit-23' },
  { q: '232', label: 'digit-232' },
  { q: '香??', label: 'wildcard' },
  { q: '開心', label: 'lookup' },
  { q: '23就=', label: 'rhyme-anchor' },
  { q: '=就?', label: 'initial-anchor' },
];

const limits = [400, 600, 800, 1000, 1200, 1500, 2000];

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);

console.log('limit_ms_items total');
for (const { q, label } of queries) {
  const parts: string[] = [];
  let total: number | undefined;
  for (const limit of limits) {
    const t0 = performance.now();
    const page = await searchPage({ query: q, mode: '0243', limit, offset: 0 });
    const ms = Math.round(performance.now() - t0);
    total = page.total;
    parts.push(`${limit}:${ms}ms/${page.items.length}`);
  }
  console.log(`${label} total=${total ?? '?'}`);
  console.log('  ', parts.join(' '));
}

await db.close();