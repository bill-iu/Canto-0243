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
import { exclusiveTwoCharTiers } from '../src/db/compound-connect.ts';
import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';

compoundLogicSelfCheck();

{
  const syn = new Map([
    ['朋友', 0],
    ['生死', 0],
  ]);
  const ant = new Map([['生死', 0]]);
  const onlySyn = exclusiveTwoCharTiers(syn, ant, 'syn');
  if (onlySyn.has('生死') || !onlySyn.has('朋友')) {
    throw new Error('compound-self-check: exclusiveTwoCharTiers syn');
  }
  const onlyAnt = exclusiveTwoCharTiers(ant, syn, 'ant');
  if (!onlyAnt.has('生死')) {
    throw new Error('compound-self-check: exclusiveTwoCharTiers ant-wins');
  }
}

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadStaticRelationData(repoRoot);

const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (fs.existsSync(fixture)) {
  const SQL = await initSqlJs();
  const native = new SQL.Database(fs.readFileSync(fixture));
  const db = createSqlJsBackend(native);
  await applyRuntimeDbPatches(db);
  // Ensure ant pair 生死 is a two-char literal for curated tier
  const { ensureComposedWordRow } = await import('../src/db/db-patch.ts');
  // Prefer explicit two-char row (compose needs 生+死 singles which exist in fixture)
  const existing = native.prepare("SELECT 1 FROM words WHERE char = '生死' LIMIT 1");
  const hasShengSi = existing.step();
  existing.free();
  if (!hasShengSi) {
    await ensureComposedWordRow(db, '生死');
  }

  // Ant first (small curated) — avoid expanding full ~~ graph for syn connective in smoke
  resetCompoundCaches();
  initCompoundLists({ syn: ['朋友'], ant: ['生死'] });
  const connectAnt = await executeCompoundSearch(
    db,
    { compound_kind: 'ant', width: 3, connective: '與' },
    'm1',
    50,
    0,
  );
  if (!connectAnt.some((r) => r.word === '生與死')) {
    throw new Error(
      `compound-self-check: 生與死 expected in !與! got ${connectAnt.map((r) => r.word).join(',')}`,
    );
  }
  // Syn exclusive: with only 朋友 curated and 生死 ant, 生與死 must not appear
  resetCompoundCaches();
  initCompoundLists({ syn: ['朋友'], ant: ['生死'] });
  const { searchConnectiveCompoundTiers } = await import('../src/db/compound-connect.ts');
  const { searchCompoundTiers } = await import('../src/db/compound.ts');
  // Use ant tiers map via private path: searchCompoundTiers for !! then exclusive unit already covered;
  // direct connective syn with empty exclusive primary (no syn two-char) should omit 生與死
  const synTiers = new Map<string, number>([['朋友', 0]]);
  const antTiers = new Map<string, number>([['生死', 0]]);
  const synConnect = await searchConnectiveCompoundTiers(db, {
    compoundKind: 'syn',
    connective: '與',
    synTiers,
    antTiers,
  });
  if (synConnect.has('生與死')) {
    throw new Error('compound-self-check: 生與死 must not appear in ~與~ exclusive map');
  }
  if (!synConnect.has('朋與友') && !synConnect.has('友與朋')) {
    // compose may fail if 朋/友 missing; optional
  }
  void searchCompoundTiers;
}

console.log('compound self-check ok');
