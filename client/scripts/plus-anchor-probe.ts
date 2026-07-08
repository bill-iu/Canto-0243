/** TDD probe: plus-anchor guide failures */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { normalizeAndParse } from '../src/db/query-engine.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { searchPage } from '../src/db/query.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';

const CASES = ['23+好', '2+好3', '+門0'] as const;
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = process.argv[2] ?? path.join(repoRoot, 'lyrics.db');

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

for (const q of CASES) {
  const parsed = normalizeAndParse(q);
  const spec = buildMatchSpecForParsed(parsed);
  const page = await searchPage({ query: q, mode: '0243', limit: 5 });
  console.log(
    `${q}\tkind=${parsed.kind}\twidth=${spec?.width}\titems=${page.items.length}\thint=${page.hint ?? ''}`,
  );
}
await db.close();