/** ponytail: real lyrics.db 近反義 pool probe (manual + mirror seeds). */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { projectRelationPool } from '../src/db/relation-pool-projection.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'client/public/lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`missing ${dbPath}`);
}

loadStaticRelationData(repoRoot);
const SQL = await initSqlJs();
const native = new SQL.Database(fs.readFileSync(dbPath));
const db = createSqlJsBackend(native);

const seeds = ['開心', '健壯', '仙', '自作多情', '寂寞', '年輕'];
for (const q of seeds) {
  const pool = await projectRelationPool(db, q);
  const synN = pool.syns.length;
  const antN = pool.ants.length;
  if (synN + antN < 1) {
    throw new Error(`pwa-relation-probe: ${q} empty syn=${synN} ant=${antN}`);
  }
  console.log(
    `${q}: syn=${synN} ant=${antN} sample=${[...pool.syns, ...pool.ants]
      .slice(0, 4)
      .map((i) => i.char)
      .join(',')}`,
  );
}
console.log('pwa-relation-probe ok');
