/**
 * Smoke-check: guide examples that once returned 0 results (parity with scripts/check_guide_examples.py).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { initCompoundLists, parseCompoundList } from '../src/db/compound.ts';
import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests } from '../src/db/init.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { queryEngine } from '../src/db/query-engine.ts';

const GUIDE_ZERO_CASES = [
  '?4困=4潦=9倒=',
  '!你',
  '33!開心',
  '!與!',
  '~與~',
] as const;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

function loadCompoundListsFromDisk(): void {
  const synPath = path.join(repoRoot, 'data/syn_ant/compound_synonyms.txt');
  const antPath = path.join(repoRoot, 'data/syn_ant/compound_antonyms.txt');
  const syn = fs.existsSync(synPath) ? parseCompoundList(fs.readFileSync(synPath, 'utf8')) : [];
  const ant = fs.existsSync(antPath) ? parseCompoundList(fs.readFileSync(antPath, 'utf8')) : [];
  initCompoundLists({ syn, ant });
}

loadRankingData(repoRoot);
loadStaticRelationData(repoRoot);
loadRhymeLetterData(repoRoot);
loadCompoundListsFromDisk();

const defaultDb = [
  path.join(repoRoot, 'tests/fixtures/lyrics.db'),
  path.join(repoRoot, 'lyrics.db'),
  path.join(repoRoot, 'client/public/lyrics.db'),
].find((p) => fs.existsSync(p));
const dbPath = process.argv[2] ?? defaultDb;
if (!dbPath) {
  throw new Error('no lyrics.db found (pass path as argv[2])');
}

const SQL = await initSqlJs();
const db = createSqlJsBackend(new SQL.Database(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);

const failures: string[] = [];
for (const q of GUIDE_ZERO_CASES) {
  const result = await queryEngine.execute({ q, mode: 'm1', limit: 5, offset: 0 });
  const n = result.items.length;
  if (!n) {
    failures.push(q);
  }
  console.log(`${n}\t${q}`);
}

if (failures.length) {
  throw new Error(`PWA guide examples FAIL (${failures.length}/${GUIDE_ZERO_CASES.length}): ${failures.join(', ')}`);
}
console.log(`PWA guide examples OK (${GUIDE_ZERO_CASES.length}/${GUIDE_ZERO_CASES.length})`);
