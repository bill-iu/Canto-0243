/** ADR-0032: 啟動完畢 tail — 輔助索引 + 靜態詞林埠預熱 */

import { ensureGateAuxiliaryIndexes } from './auxiliary-indexes.ts';
import { ensureStaticRelationIndexes } from './init.ts';

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