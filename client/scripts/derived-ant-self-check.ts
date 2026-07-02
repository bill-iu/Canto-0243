/** ponytail: derived ant smoke test (mirrors test_relation_journey) */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildRelationPool } from '../src/db/relation-pool.ts';
import { derivedAntLogicSelfCheck } from '../src/db/derived-ant.ts';
import {
  initStaticCilinSynIndex,
  initStaticSynIndex,
  resetStaticSynIndex,
} from '../src/db/thesaurus.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

resetStaticSynIndex();
initStaticCilinSynIndex({ 悲傷: ['傷心', '難過'] });
initStaticSynIndex({ 悲傷: ['傷心', '哀愁'] });

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
const words = [['快樂', 1], ['悲傷', 2], ['傷心', 3], ['哀愁', 4]];
for (const [ch, id] of words) {
  db.run('INSERT INTO words (id, char, code, jyutping, length) VALUES (?, ?, ?, ?, ?)', [
    id,
    ch,
    '22',
    '',
    ch.length,
  ]);
}
db.run(
  'INSERT INTO word_relations (id, word_id, related_id, relation_type, score, source) VALUES (1, 1, 2, ?, 0.9, ?)',
  ['ant', 'guotong'],
);

derivedAntLogicSelfCheck(db);

const pool = buildRelationPool(db, '快樂');
const bySource = Object.fromEntries(pool.ants.map((r) => [r.char, r.source]));
if (bySource['傷心'] !== 'ant_cilin_exanded') {
  throw new Error(`derived-ant-self-check: 傷心 source ${bySource['傷心']}`);
}
if (bySource['哀愁'] !== 'ant_syn_mirror') {
  throw new Error(`derived-ant-self-check: 哀愁 source ${bySource['哀愁']}`);
}
if (!bySource['悲傷']) {
  throw new Error('derived-ant-self-check: missing 悲傷');
}

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
// full loader optional — inline maps suffice for this test
void repoRoot;

console.log('derived-ant self-check ok');
