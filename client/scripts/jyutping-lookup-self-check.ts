/** PR#1: jyutping_lookup family — nei hou / ming4 baak6 on fixture db. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { jyutpingMatchSelfCheck } from '../src/db/jyutping-match.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { searchPage } from '../src/db/query.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';

const CASES = ['nei hou', 'ming4 baak6'] as const;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`missing lyrics.db: ${dbPath}`);
}

jyutpingMatchSelfCheck();

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

for (const q of CASES) {
  const page = await searchPage({ query: q, mode: '0243', limit: 5 });
  if (!page.items.length) {
    throw new Error(`jyutping-lookup-self-check: ${q} returned 0`);
  }
  console.log(`ok\t${q}\t${page.items.length}`);
}

await db.close();
console.log('jyutping-lookup-self-check: ok');