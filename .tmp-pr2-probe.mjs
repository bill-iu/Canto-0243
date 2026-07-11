import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(repoRoot, 'client'));

const { applyRuntimeDbPatches } = await import('./src/db/db-patch.ts');
const { injectDatabaseForTests, resetDatabase } = await import('./src/db/init.ts');
const { openSqlJsDatabase } = await import('./src/db/sqljs-backend.ts');
const { searchPage } = await import('./src/db/query.ts');
const { warmGuideProbeReadiness } = await import('./src/probe-readiness.node.ts');
const { normalizeAndParse } = await import('./src/db/query-engine.ts');
const { buildMatchSpecForParsed } = await import('./src/db/position-match/match-spec-registry.ts');

const CASES = ['?困潦倒=', '+香??', '?+你?'];
const dbPath = path.join(repoRoot, 'lyrics.db');
resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

for (const q of CASES) {
  const parsed = normalizeAndParse(q);
  const spec = buildMatchSpecForParsed(parsed);
  const page = await searchPage({ query: q, mode: '0243', limit: 5 });
  console.log(JSON.stringify({ q, kind: parsed.kind, spec, items: page.items.length, hint: page.hint }));
}
await db.close();