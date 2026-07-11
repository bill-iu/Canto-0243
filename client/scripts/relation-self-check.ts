/**
 * TDD: relation guide parity (~開心, !你, 33!開心, ~~, !!, !與!, ~與~).
 * Run: npx tsx client/scripts/relation-self-check.ts [db-path]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { resetCompoundCaches } from '../src/db/compound.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { QueryKind } from '../src/db/query-kind.ts';
import { normalizeAndParse } from '../src/db/query-engine.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { searchPage } from '../src/db/query.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';

const PARSE_CASES: Array<[string, QueryKind]> = [
  ['~開心', QueryKind.RELATION_LOOKUP],
  ['!你', QueryKind.RELATION_LOOKUP],
  ['33!開心', QueryKind.RELATION_LOOKUP],
  ['~~', QueryKind.COMPOUND_SYN],
  ['!!', QueryKind.COMPOUND_ANT],
  ['!與!', QueryKind.COMPOUND_ANT],
  ['~與~', QueryKind.COMPOUND_SYN],
];

const SEARCH_CASES = [
  '~開心',
  '!你',
  '33!開心',
  '~~',
  '!!',
  '!與!',
  '~與~',
] as const;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const defaultDb = [
  path.join(repoRoot, 'tests/fixtures/lyrics.db'),
  path.join(repoRoot, 'lyrics.db'),
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
loadStaticRelationData(repoRoot);

const failures: string[] = [];
for (const q of SEARCH_CASES) {
  const page = await searchPage({ query: q, mode: 'm1', limit: 5 });
  if (!page.items.length) failures.push(q);
}
// Regression: relation snapshots must not leak across DB/runtime probes.
resetCompoundCaches();
if (!(await searchPage({ query: '~與~', mode: 'm1', limit: 1 })).items.length) {
  failures.push('~與~ (after cache reset)');
}
await db.close();

if (failures.length) {
  throw new Error(`relation search FAIL: ${failures.join(', ')} (db=${dbPath})`);
}
console.log(
  `relation-self-check: ok (${SEARCH_CASES.length} queries, db=${path.basename(dbPath)})`,
);
