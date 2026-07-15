/**
 * TDD: jyutping-anchor guide parity (3+ngo4, 3$漢4, 23+o).
 * Run: npx tsx client/scripts/jyutping-anchor-self-check.ts [db-path]
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
  ['3+ngo4', QueryKind.JYUTPING_ANCHOR],
  ['3$漢4', QueryKind.JYUTPING_ANCHOR],
  ['23+o', QueryKind.JYUTPING_ANCHOR],
  ['34p', QueryKind.JYUTPING_ANCHOR],
  ['34+p', QueryKind.JYUTPING_ANCHOR],
  ['3+p4', QueryKind.JYUTPING_ANCHOR],
  ['3?p4', QueryKind.JYUTPING_ANCHOR],
  ['34gw', QueryKind.JYUTPING_ANCHOR],
  ['3+gw4', QueryKind.JYUTPING_ANCHOR],
];

const SEARCH_CASES = ['3+ngo4', '3$漢4', '23+o', '34p', '3+p4'] as const;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const defaultDb = [
  path.join(repoRoot, 'lyrics.db'),
  path.join(repoRoot, 'tests/fixtures/lyrics.db'),
].find((p) => fs.existsSync(p));
const dbPath = process.argv[2] ?? defaultDb;
if (!dbPath) {
  throw new Error('no lyrics.db (pass path as argv[2])');
}

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

for (const [q, kind] of PARSE_CASES) {
  const parsed = normalizeAndParse(q);
  if (parsed.kind !== kind) {
    throw new Error(`parse ${q}: got ${parsed.kind}, want ${kind}`);
  }
}

const failures: string[] = [];
for (const q of SEARCH_CASES) {
  const page = await searchPage({ query: q, mode: '0243', limit: 5 });
  if (!page.items.length) failures.push(q);
}
await db.close();

if (failures.length) {
  throw new Error(`jyutping-anchor search FAIL: ${failures.join(', ')} (db=${dbPath})`);
}
console.log(
  `jyutping-anchor-self-check: ok (${SEARCH_CASES.length} queries, db=${path.basename(dbPath)})`,
);