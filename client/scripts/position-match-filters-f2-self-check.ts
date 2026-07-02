/** ponytail: MF-5 F2 — final_anchor / initial_anchor filter parity vs executors */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { injectDatabaseForTests } from '../src/db/init.ts';
import { applyMatchSpec } from '../src/db/position-match/filters.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';
import { getCandidatesForLength } from '../src/db/position-match/sources.ts';
import { getWordText } from '../src/db/position-match/word-row.ts';
import { normalizeAndParse, queryEngine } from '../src/db/query-engine.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);

const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(fixture)) {
  throw new Error(`position-match-filters-f2-self-check: missing ${fixture}`);
}

const SQL = await initSqlJs();
const db = new SQL.Database(fs.readFileSync(fixture));
injectDatabaseForTests(db);

const cases = ['窮?潦倒=', '=窮?潦倒', '就=', '04困=49倒='] as const;

for (const q of cases) {
  const parsed = normalizeAndParse(q);
  const spec = buildMatchSpecForParsed(parsed);
  if (!spec) {
    throw new Error(`position-match filters F2: no spec for ${q}`);
  }
  const [candidates] = getCandidatesForLength(db, spec.width, { mode: 'm1' });
  const viaFilter = applyMatchSpec(spec, candidates, db, 'm1')
    .map((row) => getWordText(row))
    .sort();
  const viaExecutor = (
    await queryEngine.execute({ q, mode: 'm1', limit: 200, offset: 0 })
  ).items
    .map((row) => row.word)
    .sort();
  if (viaFilter.join('\0') !== viaExecutor.join('\0')) {
    throw new Error(
      `position-match filters F2: ${q} mismatch\n  filter: ${viaFilter.join(',')}\n  engine: ${viaExecutor.join(',')}`,
    );
  }
}

injectDatabaseForTests(null);
db.close();
console.log('position-match filters F2 self-check ok');
