/**
 * Node probe warmup — 對齊 PWA 就緒閘解鎖（閘前輔助索引 + 事業探針；唔等 tail）。
 * ponytail: browser path uses ensureGateAuxiliaryIndexes + validateOfflineReadiness
 */
import fs from 'node:fs';
import path from 'node:path';

import { initCompoundLists, parseCompoundList } from './db/compound.ts';
import { OFFLINE_READINESS_PROBE_QUERY, searchPage } from './db/query.ts';
import { loadRankingData } from './db/ranking-loader.node.ts';
import { loadRhymeLetterData } from './db/rime-index-loader.node.ts';

let gateAuxLoaded = false;

function loadCompoundListsFromDisk(repoRoot: string): void {
  const synPath = path.join(repoRoot, 'data/syn_ant/compound_synonyms.txt');
  const antPath = path.join(repoRoot, 'data/syn_ant/compound_antonyms.txt');
  const syn = fs.existsSync(synPath) ? parseCompoundList(fs.readFileSync(synPath, 'utf8')) : [];
  const ant = fs.existsSync(antPath) ? parseCompoundList(fs.readFileSync(antPath, 'utf8')) : [];
  initCompoundLists({ syn, ant });
}

/** 載入閘前輔助索引（韻母字母表、排序、複合詞表）。須先 injectDatabase + patches。 */
export async function warmGuideProbeReadiness(repoRoot: string): Promise<void> {
  if (!gateAuxLoaded) {
    loadRankingData(repoRoot);
    loadRhymeLetterData(repoRoot);
    loadCompoundListsFromDisk(repoRoot);
    gateAuxLoaded = true;
  }

  const page = await searchPage({
    query: OFFLINE_READINESS_PROBE_QUERY,
    mode: '0243',
    limit: 10,
  });
  const ok = page.items.some((row) => row.word === OFFLINE_READINESS_PROBE_QUERY);
  if (!ok) {
    throw new Error(
      `guide probe readiness: ${OFFLINE_READINESS_PROBE_QUERY} returned 0 rows`,
    );
  }
}

export function resetGuideProbeReadinessForTests(): void {
  gateAuxLoaded = false;
}