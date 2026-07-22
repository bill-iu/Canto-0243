import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { runStatement } from '../src/db/database-backend.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import type { ReplacementPlanV1 } from '../src/workbench/contracts.ts';
import { PwaCandidateSnapshotStore } from '../src/workbench/pwa-candidate-snapshot.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const SQL = await initSqlJs();
const native = new SQL.Database(fs.readFileSync(path.join(repoRoot, 'tests/fixtures/lyrics.db')));
const db = createSqlJsBackend(native);
const plan: ReplacementPlanV1 = {
  version: 1,
  selectionVersion: 1,
  width: 1,
  mode: 'm1',
  slots: [],
  semanticIntent: 'off',
  limit: 2,
  offset: 0,
};
const store = new PwaCandidateSnapshotStore();
(globalThis as typeof globalThis & { window?: unknown }).window = {};
let yieldedToMain = false;
setTimeout(() => { yieldedToMain = true; }, 0);
const first = await store.page(plan, db);
delete (globalThis as typeof globalThis & { window?: unknown }).window;
if (!yieldedToMain) throw new Error('sql.js snapshot build blocked the main event loop');
await runStatement(
  db,
  'INSERT INTO words (char, jyutping, code, length) VALUES (?, ?, ?, ?)',
  ['㐀', 'jau1', '3', 1],
);
const second = await store.page({ ...plan, selectionVersion: 2, offset: 2 }, db);
const freshDb = createSqlJsBackend(new SQL.Database(native.export()));
const fresh = await new PwaCandidateSnapshotStore().page(plan, freshDb);

if (second.engineTotal !== first.engineTotal || second.selectionVersion !== 2) {
  throw new Error('same PWA snapshot did not preserve immutable pool');
}
if (fresh.engineTotal !== first.engineTotal + 1) {
  throw new Error('fresh PWA snapshot did not observe lexicon change');
}

const latestStore = new PwaCandidateSnapshotStore();
const obsolete = latestStore.page(plan, freshDb);
const latest = latestStore.page({ ...plan, width: 2 }, freshDb);
const [obsoleteResult, latestResult] = await Promise.allSettled([obsolete, latest]);
if (obsoleteResult.status !== 'rejected' || latestResult.status !== 'fulfilled') {
  throw new Error('PWA snapshot latest-wins cancellation failed');
}
await db.close();
await freshDb.close();
console.log('workbench candidate snapshot self-check ok');
