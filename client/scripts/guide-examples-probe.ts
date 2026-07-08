/** 教學探針全量閘 — PWA 端（預設 repo lyrics.db；CI 用 guide-examples-self-check）。 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { searchPage } from '../src/db/query.ts';
import { allGuideExamples } from '../src/guide-examples.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

const defaultDb = [
  path.join(repoRoot, 'lyrics.db'),
  path.join(repoRoot, 'client/public/lyrics.db'),
  path.join(repoRoot, 'tests/fixtures/lyrics.db'),
].find((p) => fs.existsSync(p));
const dbPath = process.argv[2] ?? defaultDb;
if (!dbPath) {
  throw new Error('no lyrics.db found (pass path as argv[2])');
}

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

const failures: { mode: string; query: string }[] = [];
for (const ex of allGuideExamples()) {
  const p = await searchPage({ query: ex.query, mode: ex.mode, limit: 20 });
  if (!p.items.length) failures.push({ mode: ex.mode, query: ex.query });
}

console.log(`guide total=${allGuideExamples().length} fail=${failures.length}`);
for (const f of failures) console.log(`FAIL\t${f.mode}\t${f.query}`);

await db.close();
process.exit(failures.length ? 1 : 0);