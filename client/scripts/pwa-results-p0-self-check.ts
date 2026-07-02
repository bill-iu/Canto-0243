/** ponytail: P0 results UI — lookup resultType + digit-code total for load-more */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { searchPage, SEARCH_PAGE_SIZE } from '../src/db/query.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`pwa-results-p0-self-check: missing ${dbPath}`);
}

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);

const lookup = await searchPage({ query: '事業', mode: '0243', limit: SEARCH_PAGE_SIZE });
const kinds = lookup.items.map((r) => r.resultType);
if (!kinds.includes('code') || !kinds.includes('jyutping') || !kinds.includes('word')) {
  throw new Error(`pwa-results-p0-self-check: lookup missing sections: ${kinds.join(',')}`);
}
if (!lookup.total || lookup.total < lookup.items.length) {
  throw new Error(`pwa-results-p0-self-check: lookup total=${lookup.total}`);
}

const digit = await searchPage({ query: '22', mode: '0243', limit: 5, offset: 0 });
if (!digit.total || digit.total <= 5) {
  throw new Error(`pwa-results-p0-self-check: digit total=${digit.total}`);
}
const page2 = await searchPage({ query: '22', mode: '0243', limit: 5, offset: 5 });
if (!page2.items.length) {
  throw new Error('pwa-results-p0-self-check: digit page2 empty');
}

db.close();
console.log('pwa-results-p0 self-check ok:', lookup.items.length, 'lookup rows, digit total', digit.total);
