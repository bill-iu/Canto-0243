/** ponytail: digit code ranking — needs repo lyrics.db + ranking data */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { searchWords } from '../src/db/query-engine.ts';

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

db.close();
console.log('digit-code-ranking self-check ok:', words.slice(0, 5).join(', '));
