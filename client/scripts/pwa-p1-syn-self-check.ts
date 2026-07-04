/** ponytail: P1 syn_mode_page — pool browse + jyutping reject */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import { buildRelationPool } from '../src/db/relation-pool.ts';
import {
  JYUTPING_SYN_MODE_HINT,
  queryEngine,
} from '../src/db/query-engine.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadStaticRelationData(repoRoot);

const SQL = await initSqlJs();
const raw = new SQL.Database();
raw.run(`
  CREATE TABLE words (
    id INTEGER PRIMARY KEY, char TEXT, code TEXT, jyutping TEXT, length INTEGER
  )
`);
raw.run(`
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
  raw.run('INSERT INTO words (id, char, code, jyutping, length) VALUES (?, ?, ?, ?, ?)', [
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
  raw.run(
    'INSERT INTO word_relations (id, word_id, related_id, relation_type, score, source) VALUES (?, ?, ?, ?, ?, ?)',
    [i + 1, w, r, t, s, src],
  );
}

resetDatabase();
const db = createSqlJsBackend(raw);
injectDatabaseForTests(db);

const snapshot = buildRelationPool(db, '開心');
if (!snapshot.syns.length || !snapshot.ants.length) {
  throw new Error('pwa-p1-syn-self-check: empty syn/ant pool');
}

const pool = await queryEngine.execute({ q: '開心', mode: 'syn', limit: 20, offset: 0 });
const poolWords = pool.items.map((r) => r.word);
if (!poolWords.includes('愉快')) {
  throw new Error(`pwa-p1-syn-self-check: missing 愉快 in ${poolWords.join(',')}`);
}
if (!pool.items.every((r) => r.relation === 'syn')) {
  throw new Error('pwa-p1-syn-self-check: first page should be syn-only slice');
}

const jyut = await queryEngine.execute({ q: 'ming4', mode: 'syn', limit: 10, offset: 0 });
if (jyut.items.length || jyut.hint !== JYUTPING_SYN_MODE_HINT) {
  throw new Error(`pwa-p1-syn-self-check: jyutping reject hint=${jyut.hint}`);
}

db.close();
console.log('pwa-p1-syn self-check ok:', poolWords.slice(0, 6).join(', '));
