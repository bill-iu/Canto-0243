/**
 * TDD: plus-anchor guide parity (23+好, 2+好3; +門0 via mask fast path).
 * Run: npx tsx client/scripts/plus-anchor-self-check.ts [db-path]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { QueryKind } from '../src/db/query-kind.ts';
import { normalizeAndParse } from '../src/db/query-engine.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { searchPage } from '../src/db/query.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';

const PARSE_CASES: Array<[string, QueryKind]> = [
  ['23+好', QueryKind.PLUS_ANCHOR],
  ['2+好3', QueryKind.PLUS_ANCHOR],
  ['+門0', QueryKind.MASK],
];

const SEARCH_CASES = ['23+好', '2+好3', '+門0'] as const;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const defaultDb = [
  path.join(repoRoot, 'lyrics.db'),
  path.join(repoRoot, 'tests/fixtures/lyrics.db'),
].find((p) => fs.existsSync(p));
const dbPath = process.argv[2] ?? defaultDb;
if (!dbPath) {
  throw new Error('no lyrics.db (pass path as argv[2])');
}

for (const [q, kind] of PARSE_CASES) {
  const parsed = normalizeAndParse(q);
  if (parsed.kind !== kind) {
    throw new Error(`parse ${q}: got ${parsed.kind}, want ${kind}`);
  }
}

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

const failures: string[] = [];
for (const q of SEARCH_CASES) {
  const page = await searchPage({ query: q, mode: '0243', limit: 5 });
  if (!page.items.length) {
    failures.push(q);
  }
}
await db.close();

if (failures.length) {
  throw new Error(`plus-anchor search FAIL: ${failures.join(', ')} (db=${dbPath})`);
}
console.log(`plus-anchor-self-check: ok (${SEARCH_CASES.length} queries, db=${path.basename(dbPath)})`);