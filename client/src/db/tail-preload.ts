/** ADR-0032: 啟動完畢 tail — 輔助索引 + 靜態詞林埠預熱 */

import { loadCompoundListsFromUrl } from './compound.ts';
import { ensureStaticRelationIndexes } from './init.ts';
import { publicAssetUrl } from './lexicon-manifest.ts';
import { initRankingData } from './ranking.ts';
import { initRhymeLetterIndex } from './rime-index.ts';

type TailListener = (progress: number) => void;

let tailPromise: Promise<void> | null = null;
let tailComplete = false;
let tailProgress = 0;
let rankingLoaded = false;

const tailListeners = new Set<TailListener>();

function setTailProgress(value: number): void {
  tailProgress = Math.max(0, Math.min(100, Math.round(value)));
  for (const fn of tailListeners) fn(tailProgress);
}

async function loadBrowserRankingIndex(): Promise<void> {
  if (rankingLoaded) return;
  try {
    const res = await fetch(publicAssetUrl('ranking-index.json'));
    if (res.ok) initRankingData(await res.json());
  } catch {
    /* ponytail: lexical fallback */
  }
  rankingLoaded = true;
}

async function loadBrowserRhymeLetterIndex(): Promise<void> {
  try {
    const res = await fetch(publicAssetUrl('rhyme-letter-index.json'));
    if (res.ok) initRhymeLetterIndex(await res.json());
  } catch {
    /* ponytail: empty rhyme_letters options */
  }
}

async function loadBrowserCompoundLists(): Promise<void> {
  try {
    await loadCompoundListsFromUrl(import.meta.env.BASE_URL);
  } catch {
    /* optional curated lists */
  }
}

async function loadAuxiliaryIndexes(onSlice: (p: number) => void): Promise<void> {
  let done = 0;
  const tick = () => {
    done += 1;
    onSlice(done / 2);
  };
  await Promise.all([
    loadBrowserRhymeLetterIndex().then(tick),
    loadBrowserCompoundLists().then(tick),
  ]);
  void loadBrowserRankingIndex();
}

export function isStartupComplete(): boolean {
  return tailComplete;
}

export function getTailProgress(): number {
  return tailProgress;
}

export function subscribeTailProgress(fn: TailListener): () => void {
  tailListeners.add(fn);
  fn(tailProgress);
  return () => tailListeners.delete(fn);
}

export function startTailPreload(): Promise<void> {
  if (tailComplete) return Promise.resolve();
  if (tailPromise) return tailPromise;

  tailPromise = (async () => {
    setTailProgress(5);
    await loadAuxiliaryIndexes((p) => setTailProgress(5 + p * 0.45));
    setTailProgress(55);
    await ensureStaticRelationIndexes();
    setTailProgress(100);
    tailComplete = true;
  })().catch((err) => {
    tailPromise = null;
    console.warn('Tail preload failed (degraded):', err);
    setTailProgress(100);
    tailComplete = true;
  });

  return tailPromise;
}

export function resetTailPreload(): void {
  tailPromise = null;
  tailComplete = false;
  tailProgress = 0;
  rankingLoaded = false;
  tailListeners.clear();
}