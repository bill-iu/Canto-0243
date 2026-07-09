/**
 * V1: equals-family empty-result regression — four user queries + L1 per-char fallback.
 * Uses root lyrics.db (SSOT). Run: cmd /c "cd client && npx tsx scripts/equals-family-self-check.ts"
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { normalizeAndParse } from '../src/db/query-engine.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';
import { queryWordsByEqualsSpec } from '../src/db/position-match/equals-filters.ts';
import {
  filterMatchSpecRows,
  narrowingCodeFromSpec,
} from '../src/db/position-match/engine.ts';
import { getEqualsSpan } from '../src/db/position-match/spec.ts';
import { queryFirst } from '../src/db/database-backend.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`equals-family-self-check: missing ${dbPath}`);
}

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);

async function countForQuery(q: string): Promise<number> {
  const parsed = normalizeAndParse(q);
  const spec = buildMatchSpecForParsed(parsed);
  if (!spec) {
    throw new Error(`equals-family-self-check: no spec for ${q}`);
  }
  const span = getEqualsSpan(spec);
  if (span) {
    return (await queryWordsByEqualsSpec(spec, db, 'm1')).length;
  }
  return (await filterMatchSpecRows(spec, { db, mode: 'm1' })).length;
}

const mustHit = ['?困潦倒=', '+門=0', '0449窮困潦倒=', '04困=49倒='] as const;
for (const q of mustHit) {
  const n = await countForQuery(q);
  if (n < 1) {
    throw new Error(`equals-family-self-check: ${q} expected n>0 got ${n}`);
  }
  console.log(`ok ${q} n=${n}`);
}

// C1 unit: serial mask 0449 → narrowing code
{
  const spec = buildMatchSpecForParsed(normalizeAndParse('04困=49倒='))!;
  const code = narrowingCodeFromSpec(spec);
  if (code !== '0449') {
    throw new Error(`equals-family-self-check: narrowing 04困=49倒= got ${code}`);
  }
  console.log('ok narrowingCodeFromSpec 04困=49倒= → 0449');
}

// L1: prefix-wildcard still works when multi-char headword absent (simulate by only requiring n>0 on root;
// if 困潦倒 missing, per-char path must still yield). Soft-check: 困/潦/倒 singles exist.
for (const ch of ['困', '潦', '倒']) {
  const row = await queryFirst(db, 'SELECT char FROM words WHERE char = ? LIMIT 1', [ch]);
  if (!row) {
    throw new Error(`equals-family-self-check: missing single-char ${ch} for L1`);
  }
}
console.log('ok L1 single-char anchors present');

// 香港= control
const nHk = await countForQuery('香港=');
if (nHk < 1) {
  throw new Error(`equals-family-self-check: 香港= empty`);
}
console.log(`ok 香港= n=${nHk}`);

injectDatabaseForTests(null);
await db.close();
console.log('equals-family-self-check ok');
