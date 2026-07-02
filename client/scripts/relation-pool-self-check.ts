/** ponytail: relation pool smoke test (seed_happy_sad equivalent) */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { relationLookupItems, relationPoolLogicSelfCheck } from '../src/db/relation-pool.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadStaticRelationData(repoRoot);

const SQL = await initSqlJs();
const db = new SQL.Database();
db.run(`
  CREATE TABLE words (
    id INTEGER PRIMARY KEY, char TEXT, code TEXT, jyutping TEXT, length INTEGER
  )
`);
db.run(`
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
];
for (let i = 0; i < words.length; i++) {
  const [ch, code, len] = words[i]!;
  db.run('INSERT INTO words (id, char, code, jyutping, length) VALUES (?, ?, ?, ?, ?)', [
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
];
for (let i = 0; i < rels.length; i++) {
  const [w, r, t, s, src] = rels[i]!;
  db.run(
    'INSERT INTO word_relations (id, word_id, related_id, relation_type, score, source) VALUES (?, ?, ?, ?, ?, ?)',
    [i + 1, w, r, t, s, src],
  );
}

relationPoolLogicSelfCheck(db);

const items = relationLookupItems(db, '開心', 'syn', 'm1', undefined, 20, 0);
const chars = items.map((i) => i.char).sort();
if (chars.join(',') !== '快樂,愉快') {
  throw new Error(`relation-pool-self-check: ~開心 syns ${chars.join(',')}`);
}

console.log('relation-pool self-check ok');
