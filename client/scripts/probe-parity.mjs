import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { searchPage } from '../src/db/query.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadRhymeLetterData(repoRoot);

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(path.join(repoRoot, 'lyrics.db'))));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);

for (const [q, mode] of [
  ['04困=49倒=', '0243'],
  ['?4困=4潦=9倒=', '0243'],
  ['PZ', '394052'],
  ['?+m?', '0243'],
]) {
  const p = await searchPage({ query: q, mode, limit: 20 });
  console.log(`client\t${q}\t${p.items.length}\t${p.total ?? ''}`);
}
await db.close();