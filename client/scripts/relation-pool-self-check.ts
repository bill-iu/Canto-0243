/** ponytail: relation pool smoke test (seed_happy_sad equivalent) */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildRelationPool } from '../src/db/relation-pool/builder.ts';
import {
  invalidateRelationPoolCache,
  projectRelationPool,
  relationLookupItems,
  relationPoolLogicSelfCheck,
} from '../src/db/relation-pool/projection.ts';
import {
  getLexiconMembership,
  invalidateLexiconMembership,
  isLexiconMembershipReady,
} from '../src/db/lexicon-membership.ts';
import {
  projectAntRankingSelfCheck,
  projectSynRankingSelfCheck,
} from '../src/db/relation-pool/ranking.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

projectAntRankingSelfCheck();
projectSynRankingSelfCheck();

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadStaticRelationData(repoRoot);

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
const words = [
  ['快樂', '22', 2],
  ['開心', '22', 2],
  ['愉快', '22', 2],
  ['悲傷', '22', 2],
  ['傷心', '22', 2],
  ['走', '22', 1],
  ['留', '22', 1],
];
for (let i = 0; i < words.length; i++) {
  const [ch, code, len] = words[i]!;
  native.run('INSERT INTO words (id, char, code, jyutping, length) VALUES (?, ?, ?, ?, ?)', [
    i + 1,
    ch,
    code,
    '',
    len,
  ]);
}
const rels = [
  [1, 2, 'syn', 0.95, 'cilin'],
  [1, 3, 'syn', 0.8, 'test'],
  [2, 4, 'ant', 0.9, 'guotong'],
  [2, 5, 'ant', 0.7, 'ant_syn_bridge'],
  // project_ant row present; same-char guotong vs project_ant merge covered by ranking self-check
  [6, 7, 'ant', 0.85, 'project_ant'],
];
for (let i = 0; i < rels.length; i++) {
  const [w, r, t, s, src] = rels[i]!;
  native.run(
    'INSERT INTO word_relations (id, word_id, related_id, relation_type, score, source) VALUES (?, ?, ?, ?, ?, ?)',
    [i + 1, w, r, t, s, src],
  );
}

const db = createSqlJsBackend(native);
await relationPoolLogicSelfCheck(db);

const snapshot = await buildRelationPool(db, '開心');
const snapshotChars = snapshot.chars('syn');
if (!snapshotChars.includes('快樂') || !snapshotChars.includes('愉快')) {
  throw new Error(`relation-pool-self-check: snapshot chars ${snapshotChars.join(',')}`);
}
const walkPool = await buildRelationPool(db, '走');
const walkAnt = walkPool.ants.find((i) => i.char === '留');
if (!walkAnt || walkAnt.source !== 'project_ant') {
  throw new Error(
    `relation-pool-self-check: project_ant 走→留 got ${walkAnt?.source ?? 'missing'}`,
  );
}
const firstPage = snapshot.page(1, 0).map((i) => i.char);
if (firstPage.length !== 1 || !snapshotChars.includes(firstPage[0] ?? '')) {
  throw new Error(`relation-pool-self-check: snapshot page ${firstPage.join(',')}`);
}

const items = await relationLookupItems(db, '開心', 'syn', 'm1', undefined, 20, 0);
const chars = items.map((i) => i.char).sort();
if (chars.join(',') !== '快樂,愉快') {
  throw new Error(`relation-pool-self-check: ~開心 syns ${chars.join(',')}`);
}

// PR2: membership + pool cache
invalidateLexiconMembership();
invalidateRelationPoolCache();
const mem1 = await getLexiconMembership(db);
const mem2 = await getLexiconMembership(db);
if (mem1 !== mem2 || !isLexiconMembershipReady(db)) {
  throw new Error('relation-pool-self-check: membership cache miss');
}
const p1 = await projectRelationPool(db, '開心');
const p2 = await projectRelationPool(db, '開心');
if (p1 !== p2) {
  throw new Error('relation-pool-self-check: pool LRU should return same snapshot');
}

console.log('relation-pool self-check ok');
