/** ponytail: compound module smoke test */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  compoundLogicSelfCheck,
  executeCompoundSearch,
  initCompoundLists,
  resetCompoundCaches,
} from '../src/db/compound.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

compoundLogicSelfCheck();

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);

const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (fs.existsSync(fixture)) {
  const SQL = await initSqlJs();
  const db = new SQL.Database(fs.readFileSync(fixture));
  resetCompoundCaches();
  initCompoundLists({ syn: ['朋友'], ant: [] });
  const items = executeCompoundSearch(
    db,
    { compound_kind: 'syn', width: 2 },
    'm1',
    10,
    0,
  );
  if (!Array.isArray(items)) {
    throw new Error('compound-self-check: expected array');
  }
}

console.log('compound self-check ok');
