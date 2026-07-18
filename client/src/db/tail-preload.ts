/**
 * ADR-0032 / CONTEXT § 離線啟動預載 tail + 背景預載標示.
 * After 就緒閘解鎖 only: 靜態詞林 → 詞庫字面集 → 音素倒排 (await; no gate block).
 */
import { ensureGateAuxiliaryIndexes } from './auxiliary-indexes.ts';
import { ensureStaticRelationIndexes, getDatabase, isDatabaseInitialized } from './init.ts';
import { publicAssetUrl } from './lexicon-manifest.ts';
import { getLexiconMembership } from './lexicon-membership.ts';
import { ensurePhonemeIndex } from './position-match/phoneme-index.ts';
import type { Database } from './sqljs.ts';
import { ensureProjectPosCarrier } from '../pos/carrier.ts';

type TailListener = (progress: number) => void;

let tailPromise: Promise<void> | null = null;
let tailComplete = false;
let tailProgress = 0;
const tailListeners = new Set<TailListener>();

function setTailProgress(value: number): void {
  tailProgress = Math.max(0, Math.min(100, Math.round(value)));
  for (const fn of tailListeners) fn(tailProgress);
}

function getDbOrNull(): Database | null {
  if (!isDatabaseInitialized()) return null;
  try {
    return getDatabase() as unknown as Database;
  } catch {
    return null;
  }
}

/**
 * One stage: catch → warn → continue (badge still completes; search lazy-rebuilds).
 */
async function runStage(
  label: string,
  from: number,
  to: number,
  work: () => Promise<void>,
): Promise<void> {
  setTailProgress(from);
  try {
    await work();
  } catch (err) {
    console.warn(`Tail preload stage «${label}» failed (degraded):`, err);
  }
  setTailProgress(to);
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

/**
 * Post-gate only. Never call from initializeDatabase gate path.
 * Progress: 0–40 靜態詞林 · 40–70 詞庫字面集 · 70–100 音素倒排.
 */
export function startTailPreload(): Promise<void> {
  if (tailComplete) return Promise.resolve();
  if (tailPromise) return tailPromise;

  tailPromise = (async () => {
    setTailProgress(2);

    // Idempotent; gate already loaded these — cheap hit if warm
    await runStage('gate-aux', 2, 10, async () => {
      await ensureGateAuxiliaryIndexes();
    });

    await runStage('static-relation', 10, 35, async () => {
      await ensureStaticRelationIndexes();
    });

    // ADR-0058: 詞性載體 — never blocks gate; missing → 詞性缺標
    await runStage('project-pos', 35, 42, async () => {
      await ensureProjectPosCarrier(publicAssetUrl('project-pos-index.json'));
    });

    await runStage('lexicon-membership', 42, 70, async () => {
      const db = getDbOrNull();
      if (!db) return;
      await getLexiconMembership(db);
    });

    await runStage('phoneme-index', 70, 100, async () => {
      const db = getDbOrNull();
      if (!db) return;
      await ensurePhonemeIndex(db);
    });

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
