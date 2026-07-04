/** ponytail: P5 anchor_dimension — dual 聲母/韻母 sections */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import {
  anchorResultListSelfCheck,
  hasAnchorResultLayout,
} from '../src/anchor-result-list.tsx';
import { searchPage } from '../src/db/query.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`pwa-p5-anchor-self-check: missing ${dbPath}`);
}

anchorResultListSelfCheck();

resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);

async function assertDualAnchorPage(query: string): Promise<void> {
  const limit = 200;
  let offset = 0;
  let initial = 0;
  let final = 0;
  let total = 0;

  while (offset === 0 || (initial === 0 || final === 0) && offset < total) {
    const page = await searchPage({ query, mode: '0243', limit, offset });
    if (!page.items.length) {
      throw new Error(`pwa-p5-anchor-self-check: ${query} empty`);
    }
    total = page.total ?? page.items.length;
    if (!hasAnchorResultLayout(page.items)) {
      throw new Error(`pwa-p5-anchor-self-check: ${query} missing anchor_dimension`);
    }
    initial += page.items.filter((r) => r.anchor_dimension === 'initial').length;
    final += page.items.filter((r) => r.anchor_dimension === 'final').length;
    offset += page.items.length;
    if (page.items.length < limit) break;
  }

  if (!initial || !final) {
    throw new Error(`pwa-p5-anchor-self-check: ${query} initial=${initial} final=${final}`);
  }
}

for (const query of ['?+m?'] as const) {
  await assertDualAnchorPage(query);
}

db.close();
console.log('pwa-p5-anchor-self-check: ok');
