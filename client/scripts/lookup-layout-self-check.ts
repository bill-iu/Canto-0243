/** ponytail: one-shot lookup layout self-check */
import { lookupLayoutSelfCheck } from '../src/db/query-engine.ts';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { buildLookupLayout } from '../src/db/query/lookup-layout.ts';
import { executeWordLookup } from '../src/db/query/word-lookup-executor.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { runStatement } from '../src/db/database-backend.ts';
import { QueryKind } from '../src/db/query-kind.ts';

await lookupLayoutSelfCheck();
loadRankingData(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'));
for (const [char, preferred, variant] of [
  ['長於', 'zoeng2 jyu1', 'coeng4 jyu1'],
  ['首尾相連', 'sau2 mei5 soeng1 lin4', 'sau2 mei2 soeng1 lin4'],
]) {
  const rows = [variant!, preferred!].map((jyutping) => ({ char: char!, jyutping, code: '', length: [...char!].length }));
  const result = await buildLookupLayout(char!, rows, null);
  assert.equal(result.length, 1);
  assert.equal(result[0]!.jyutping, preferred);
}
// Exercise the real executor too: it must not discard alternate readings
// before buildLookupLayout has ranked them.
const db = await openSqlJsDatabase(new Uint8Array());
try {
  await runStatement(db, 'CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, jyutping TEXT, code TEXT, initials TEXT, finals TEXT, length INTEGER, embedding TEXT)');
  const cases = [
    ['長於', 'zoeng2 jyu1', '93', 'coeng4 jyu1', '03'],
    ['首尾相連', 'sau2 mei5 soeng1 lin4', '9530', 'sau2 mei2 soeng1 lin4', '9930'],
    ['鈾礦', 'jau2 kwong3', '94', 'jau4 kwong3', '04'],
    ['烷基', 'jyun2 gei1', '93', 'jyun4 gei1', '03'],
  ] as const;
  for (const [char, preferred, code, variant, variantCode] of cases) {
    for (const [jp, toneCode] of [[variant, variantCode], [preferred, code]]) {
      await runStatement(db, 'INSERT INTO words (char,jyutping,code,initials,finals,length) VALUES (?,?,?,?,?,?)',
        [char, jp!, toneCode!, '[]', '[]', [...char].length]);
    }
  }
  for (const [char, preferred] of cases) {
    const page = await executeWordLookup({ kind: QueryKind.WORD_LOOKUP, raw_q: char }, db, 'm3', 100, 0);
    const exact = page.items.filter((row) => row.word === char);
    assert.equal(exact.length, 1);
    assert.equal(exact[0]!.jyutping, preferred);
  }
} finally {
  await db.close();
}
console.log('lookup layout self-check ok');
