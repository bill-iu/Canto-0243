/** ponytail: MF-4 executeMatchSpec vertical slice — 4 stub kinds on fixture db */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  QueryKind,
  normalizeAndParse,
  parseCodeRefMiddleRhymeQuery,
  queryEngine,
  type HybridTailEqualsAliasQuery,
  type ParsedQuery,
} from '../src/db/query-engine.ts';
import { injectDatabaseForTests } from '../src/db/init.ts';
import { executeMatchSpec } from '../src/db/position-match/engine.ts';
import { normalizeToMatchSpec } from '../src/db/position-match/match-spec-registry.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);

const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(fixture)) {
  throw new Error(`position-match-engine-self-check: missing ${fixture}`);
}

const SQL = await initSqlJs();
const db = new SQL.Database(fs.readFileSync(fixture));

type Case = { label: string; parsed: ParsedQuery; expectCount: number };

const cases: Case[] = [
  {
    label: '?30人',
    parsed: normalizeAndParse('?30人'),
    expectCount: 0,
  },
  {
    label: '?+人=?',
    parsed: normalizeAndParse('?+人=?'),
    expectCount: 0,
  },
];

const codeRef = parseCodeRefMiddleRhymeQuery('?3人=?');
if (codeRef) {
  cases.push({ label: 'CODE_REF_MIDDLE_RHYME', parsed: codeRef, expectCount: 0 });
}

const hybridAlias: HybridTailEqualsAliasQuery = {
  kind: QueryKind.HYBRID_TAIL_EQUALS_ALIAS,
  raw_q: '23就=',
  hybrid_q: '23就',
};
cases.push({ label: 'HYBRID_TAIL_EQUALS_ALIAS', parsed: hybridAlias, expectCount: 0 });

for (const { label, parsed, expectCount } of cases) {
  const spec = normalizeToMatchSpec(parsed);
  if (!spec) {
    throw new Error(`position-match-engine-self-check: no spec for ${label}`);
  }
  const rows = executeMatchSpec(spec, { db, mode: 'm1', limit: 100, offset: 0 });
  if (rows.length !== expectCount) {
    throw new Error(
      `position-match-engine-self-check: ${label} got ${rows.length} rows, want ${expectCount}`,
    );
  }
}

const dispatchWildcard = await (async () => {
  injectDatabaseForTests(db);
  try {
    return await queryEngine.execute({
      q: '?30人',
      mode: 'm1',
      limit: 100,
      offset: 0,
    });
  } finally {
    injectDatabaseForTests(null);
  }
})();
if (dispatchWildcard.items.length !== 0) {
  throw new Error('position-match-engine-self-check: dispatch ?30人 should be empty on fixture');
}

const hybridSpec = normalizeToMatchSpec(hybridAlias);
if (!hybridSpec?.hybrid_ref_chars) {
  throw new Error('position-match-engine-self-check: hybrid alias rewrite failed');
}

db.close();
console.log('position-match engine self-check ok');
