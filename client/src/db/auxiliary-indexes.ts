/** 閘前必載輔助索引 — 粵拼錨／排序／複合詞表（CONTEXT § 離線啟動預載 閘前段） */

import { loadCompoundListsFromUrl } from './compound.ts';
import { publicAssetUrl } from './lexicon-manifest.ts';
import { initRankingData } from './ranking.ts';
import { initRhymeLetterIndex } from './rime-index.ts';

let gateAuxLoaded = false;
let rankingLoaded = false;

export async function loadBrowserRankingIndex(): Promise<void> {
  if (rankingLoaded) return;
  try {
    const res = await fetch(publicAssetUrl('ranking-index.json'));
    if (res.ok) initRankingData(await res.json());
  } catch {
    /* ponytail: lexical fallback */
  }
  rankingLoaded = true;
}

export async function loadBrowserRhymeLetterIndex(): Promise<void> {
  try {
    const res = await fetch(publicAssetUrl('rhyme-letter-index.json'));
    if (res.ok) initRhymeLetterIndex(await res.json());
  } catch {
    /* ponytail: empty rhyme_letters options */
  }
}

export async function loadBrowserCompoundLists(): Promise<void> {
  try {
    await loadCompoundListsFromUrl(import.meta.env.BASE_URL);
  } catch {
    /* optional curated lists */
  }
}

/** 就緒閘解鎖前：粵拼錨與教學範例依賴韻母字母表＋排序信號 */
export async function ensureGateAuxiliaryIndexes(): Promise<void> {
  if (gateAuxLoaded) return;
  await Promise.all([
    loadBrowserRhymeLetterIndex(),
    loadBrowserRankingIndex(),
    loadBrowserCompoundLists(),
  ]);
  gateAuxLoaded = true;
}

export function resetGateAuxiliaryIndexes(): void {
  gateAuxLoaded = false;
  rankingLoaded = false;
}