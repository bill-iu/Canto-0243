/**
 * D1: process-level relation graph cache for derived_ant dual-open.
 * Run: npx tsx scripts/relation-graph-self-check.ts  (cwd: client/)
 */
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import {
  CILIN_DERIVED_SOURCE,
  MIRROR_SOURCE,
  appendRuntimeDerivedAntPool,
  directAntSeedsForHead,
} from '../src/db/derived-ant.ts';
import {
  ensureRelationGraph,
  invalidateRelationGraph,
  isRelationGraphReady,
  relationGraphBuildCount,
  directSynNeighbors,
} from '../src/db/relation-graph.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import {
  initStaticCilinSynIndex,
  initStaticSynIndex,
  resetStaticSynIndex,
} from '../src/db/thesaurus.ts';

resetStaticSynIndex();
initStaticCilinSynIndex({ 悲傷: ['傷心', '難過'] });
initStaticSynIndex({ 悲傷: ['傷心', '哀愁'] });

const SQL = await initSqlJs();
const native = new SQL.Database();
native.run(`
  CREATE TABLE words (
    id INTEGER PRIMARY KEY, char TEXT, code TEXT, jyutping TEXT, length INTEGER
  )
`);
native.run(`
  CREATE TABLE word_relations (
    id INTEGER PRIMARY KEY, word_id INTEGER, related_id INTEGER,
    relation_type TEXT, score REAL, source TEXT, group_codes TEXT
  )
`);
const words: Array<[string, number]> = [
  ['快樂', 1],
  ['悲傷', 2],
  ['傷心', 3],
  ['哀愁', 4],
  ['難過', 5],
];
for (const [ch, id] of words) {
  native.run('INSERT INTO words (id, char, code, jyutping, length) VALUES (?, ?, ?, ?, ?)', [
    id,
    ch,
    '22',
    '',
    ch.length,
  ]);
}
// direct ant seed
native.run(
  'INSERT INTO word_relations (id, word_id, related_id, relation_type, score, source) VALUES (1, 1, 2, ?, 0.9, ?)',
  ['ant', 'guotong'],
);
// DB syn edge for mirror path (悲傷↔哀愁 already static; add 悲傷↔難過 as DB-only)
native.run(
  'INSERT INTO word_relations (id, word_id, related_id, relation_type, score, source) VALUES (2, 2, 5, ?, 0.8, ?)',
  ['syn', 'guotong'],
);

const db = createSqlJsBackend(native);
injectDatabaseForTests(db);

const membership = new Set(words.map(([ch]) => ch));
const gen0 = relationGraphBuildCount();

await ensureRelationGraph(db, membership);
if (!isRelationGraphReady(db)) {
  throw new Error('relation-graph-self-check: not ready after ensure');
}
if (relationGraphBuildCount() !== gen0 + 1) {
  throw new Error('relation-graph-self-check: expected build generation +1');
}

// Rebuild-once
await ensureRelationGraph(db, membership);
if (relationGraphBuildCount() !== gen0 + 1) {
  throw new Error('relation-graph-self-check: second ensure rebuilt graph');
}

const neigh = directSynNeighbors('悲傷');
if (!neigh.includes('難過') || !neigh.includes('傷心')) {
  throw new Error(`relation-graph-self-check: neighbors ${neigh.join(',')}`);
}

// Dual-open: two appendRuntimeDerivedAntPool share one graph build
const seeds = directAntSeedsForHead(db, '快樂', membership, true, [
  { char: '悲傷', source: 'guotong' },
]);
const headSyns = new Set<string>();
const pool1 = await appendRuntimeDerivedAntPool(
  '快樂',
  [],
  db,
  membership,
  true,
  new Set(),
  headSyns,
  [{ char: '悲傷', source: 'guotong' }],
);
const genAfterFirst = relationGraphBuildCount();
const pool2 = await appendRuntimeDerivedAntPool(
  '快樂',
  [],
  db,
  membership,
  true,
  new Set(),
  headSyns,
  [{ char: '悲傷', source: 'guotong' }],
);
if (relationGraphBuildCount() !== genAfterFirst) {
  throw new Error('relation-graph-self-check: dual-open rebuilt graph');
}

const by1 = Object.fromEntries(pool1.map((r) => [r.char, r.source]));
const by2 = Object.fromEntries(pool2.map((r) => [r.char, r.source]));
if (by1['傷心'] !== CILIN_DERIVED_SOURCE || by2['傷心'] !== CILIN_DERIVED_SOURCE) {
  throw new Error(`relation-graph-self-check: cilin ${by1['傷心']}/${by2['傷心']}`);
}
if (by1['哀愁'] !== MIRROR_SOURCE || by2['哀愁'] !== MIRROR_SOURCE) {
  throw new Error(`relation-graph-self-check: mirror ${by1['哀愁']}/${by2['哀愁']}`);
}
if (!seeds.includes('悲傷')) {
  throw new Error('relation-graph-self-check: seeds');
}

// Invalidate on inject (DB identity change path)
injectDatabaseForTests(db);
if (isRelationGraphReady(db)) {
  throw new Error('relation-graph-self-check: expected invalidate after inject');
}

await ensureRelationGraph(db, membership);
if (!isRelationGraphReady(db)) {
  throw new Error('relation-graph-self-check: not ready after rebuild');
}

invalidateRelationGraph();
if (isRelationGraphReady(db)) {
  throw new Error('relation-graph-self-check: explicit invalidate failed');
}

resetDatabase();
console.log(
  `relation-graph-self-check ok (cilin+mirror dual-open, builds=${relationGraphBuildCount() - gen0})`,
);
