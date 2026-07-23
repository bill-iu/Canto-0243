/** ponytail: digit code ranking — needs repo lyrics.db + ranking data */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { compareSearchResults } from '../src/db/ranking.ts';
import { searchWords } from '../src/db/query-engine.ts';
import type {
  ReplacementPlanV1,
  WorkbenchCandidate,
} from '../src/workbench/contracts.ts';
import { PwaCandidateSnapshotStore } from '../src/workbench/pwa-candidate-snapshot.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`digit-code-ranking-self-check: missing ${dbPath}`);
}

loadRankingData(repoRoot);
resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);

const hits = await searchWords('22', undefined, undefined, 'm1', 20, 0);
const words = hits.map((r) => r.word);
const danIdx = words.indexOf('但係');
const maiIdx = words.indexOf('係咪');
if (danIdx < 0 || maiIdx < 0) {
  throw new Error(`digit-code-ranking-self-check: missing anchors in ${words.slice(0, 10).join(',')}`);
}
if (danIdx > maiIdx) {
  throw new Error(`digit-code-ranking-self-check: 但係@${danIdx} should precede 係咪@${maiIdx}`);
}

const query302 = await searchWords('302', undefined, undefined, 'm1', 100, 0);
const main302 = [...new Set(query302.map((row) => row.word))];
const plan302: ReplacementPlanV1 = {
  version: 1,
  selectionVersion: 1,
  width: 3,
  mode: 'm1',
  slots: [
    { pos: 0, kind: 'code_digit', digit: '3' },
    { pos: 1, kind: 'code_digit', digit: '0' },
    { pos: 2, kind: 'code_digit', digit: '2' },
  ],
  semanticIntent: 'off',
  limit: 100,
};
const workbench302 = await new PwaCandidateSnapshotStore().page(plan302, db);
const candidate302 = workbench302.exact.sound_only.map((item) => item.literal);
if (candidate302.join('\n') !== main302.slice(0, candidate302.length).join('\n')) {
  throw new Error(
    `302 ranking parity failed:\nmain=${main302.slice(0, 12).join(',')}\nworkbench=${candidate302.slice(0, 12).join(',')}`,
  );
}

function assertCanonical(label: string, candidates: WorkbenchCandidate[]): void {
  const expected = [...candidates].sort((a, b) => compareSearchResults(
    { char: a.literal, jyutping: a.jyutping, code: a.code },
    { char: b.literal, jyutping: b.jyutping, code: b.code },
  ));
  const actualKey = candidates.map((item) => `${item.literal}\0${item.jyutping}`).join('\n');
  const expectedKey = expected.map((item) => `${item.literal}\0${item.jyutping}`).join('\n');
  if (actualKey !== expectedKey) {
    throw new Error(`${label} abandoned main-query canonical ranking`);
  }
}

const anchor302 = query302[0];
if (!anchor302 || Array.from(anchor302.word).length !== 3) {
  throw new Error('302 ranking parity missing a three-character anchor');
}
const anchorChars = Array.from(anchor302.word);
const anchorReadings = anchor302.jyutping.trim().split(/\s+/);
for (const kind of ['final_anchor', 'initial_anchor'] as const) {
  const constrained: ReplacementPlanV1 = {
    ...plan302,
    slots: anchorChars.map((ref, pos) => ({
      pos,
      kind,
      ref,
      refJyutping: anchorReadings[pos]!,
    })),
  };
  const response = await new PwaCandidateSnapshotStore().page(constrained, db);
  assertCanonical(kind === 'final_anchor' ? 'rhyme result' : 'initial result', response.exact.sound_only);
}

await db.close();
console.log(
  'digit-code-ranking self-check ok:',
  words.slice(0, 5).join(', '),
  '| 302 + rhyme/initial canonical parity',
);
