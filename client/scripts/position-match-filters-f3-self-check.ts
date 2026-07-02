/** ponytail: MF-5 F3 — rhyme/syllable/initial_letters + dual_phoneme filter parity */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { injectDatabaseForTests } from '../src/db/init.ts';
import { executeMatchSpec } from '../src/db/position-match/engine.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';
import { normalizeAndParse, queryEngine } from '../src/db/query-engine.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import { getWordText } from '../src/db/position-match/word-row.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);

const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(fixture)) {
  throw new Error(`position-match-filters-f3-self-check: missing ${fixture}`);
}

const SQL = await initSqlJs();
const db = new SQL.Database(fs.readFileSync(fixture));
injectDatabaseForTests(db);

const cases = ['?yut?', '3m4', '?+人=?'] as const;

for (const q of cases) {
  const parsed = normalizeAndParse(q);
  const spec = buildMatchSpecForParsed(parsed);
  if (!spec) {
    throw new Error(`position-match filters F3: no spec for ${q}`);
  }
  const viaFilter = executeMatchSpec(spec, { db, mode: 'm1', limit: 200, offset: 0 })
    .map((row) => getWordText(row))
    .sort();
  const viaExecutor = (
    await queryEngine.execute({ q, mode: 'm1', limit: 200, offset: 0 })
  ).items
    .map((row) => row.word)
    .sort();
  if (viaFilter.join('\0') !== viaExecutor.join('\0')) {
    throw new Error(
      `position-match filters F3: ${q} mismatch\n  filter: ${viaFilter.join(',')}\n  engine: ${viaExecutor.join(',')}`,
    );
  }
}

injectDatabaseForTests(null);
db.close();
console.log('position-match filters F3 self-check ok');
