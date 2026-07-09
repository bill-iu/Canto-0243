/** ADR-0032: 啟動完畢 tail — 輔助索引 + 靜態詞林埠 + 搜尋熱路徑 prewarm */

import { ensureGateAuxiliaryIndexes } from './auxiliary-indexes.ts';
import { ensureStaticRelationIndexes, getDatabase, isDatabaseInitialized } from './init.ts';
import { prewarmLexiconMembership } from './lexicon-membership.ts';
import { ensurePhonemeIndex } from './position-match/phoneme-index.ts';
import type { Database } from './sqljs.ts';

type TailListener = (progress: number) => void;

let tailPromise: Promise<void> | null = null;
let tailComplete = false;
let tailProgress = 0;
const tailListeners = new Set<TailListener>();

function setTailProgress(value: number): void {
  tailProgress = Math.max(0, Math.min(100, Math.round(value)));
  for (const fn of tailListeners) fn(tailProgress);
}

async function loadAuxiliaryIndexes(onSlice: (p: number) => void): Promise<void> {
  await ensureGateAuxiliaryIndexes();
  onSlice(1);
}

/** Non-blocking: phoneme inverted index + DISTINCT char set for 近反義. */
function prewarmSearchHotPaths(): void {
  if (!isDatabaseInitialized()) return;
  try {
    const db = getDatabase() as unknown as Database;
    prewarmLexiconMembership(db);
    void ensurePhonemeIndex(db).catch(() => {
      /* first query rebuilds */
    });
  } catch {
    /* db not ready */
  }
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
    setTailProgress(85);
    prewarmSearchHotPaths();
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
  tailListeners.clear();
}