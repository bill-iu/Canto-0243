/** ponytail: one-shot Scenario C probe — `npx tsx client/scripts/scenario-c-probe.ts` */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadRhymeLetterData(repoRoot);
loadStaticRelationData(repoRoot);

const dbPath = path.join(repoRoot, 'client/public/lyrics.dev.db');
const buf = fs.readFileSync(dbPath);

const initSqlJs = (await import('../src/db/sqljs.ts')).initSqlJs;
const { createSqlJsBackend } = await import('../src/db/sqljs-backend.ts');
const SQL = await initSqlJs();
const db = createSqlJsBackend(new SQL.Database(buf));

const { injectDatabaseForTests } = await import('../src/db/init.ts');
injectDatabaseForTests(db);

const { queryEngine } = await import('../src/db/query-engine.ts');

for (const q of ['事業', '?+m?', '窮?潦倒=']) {
  const result = await queryEngine.execute({ q, mode: 'm1', limit: 10, offset: 0 });
  const chars = result.items
    .filter((r) => r.resultType !== 'code' && r.resultType !== 'jyutping')
    .map((r) => r.word);
  console.log(q, 'total=', result.total ?? result.items.length, 'chars=', chars.join(','));
}
