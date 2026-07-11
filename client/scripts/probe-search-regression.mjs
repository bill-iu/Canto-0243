/** probe: merged vs raw counts + anchor queries */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { searchPage } from '../src/db/query.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { mergedResultCount } from '../src/result-list-logic.ts';
import { allGuideExamples } from '../src/guide-examples.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadRhymeLetterData(repoRoot);

const dbPath = path.join(repoRoot, 'lyrics.db');
resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);

for (const q of ['333', '3h4', '3hon4', '香港=', '~開心', '事業']) {
  const p = await searchPage({ query: q, mode: '0243', limit: 1200 });
  console.log(
    `${q}\titems=${p.items.length}\ttotal=${p.total}\tmerged=${mergedResultCount(p.items)}`,
  );
}

let fail = 0;
for (const ex of allGuideExamples()) {
  const p = await searchPage({ query: ex.query, mode: ex.mode, limit: 20 });
  if (!p.items.length) {
    console.log(`FAIL\t${ex.mode}\t${ex.query}`);
    fail += 1;
  }
}
console.log(`guide total=${allGuideExamples().length} fail=${fail}`);
await db.close();
