/** ADR-0032 D: 詞庫預取（非 metered / 非 saveData） */

import { getCurrentLexiconTarget } from './db/init';

function isMeteredConnection(): boolean {
  const conn = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } })
    .connection;
  if (!conn) return false;
  if (conn.saveData) return true;
  return typeof conn.effectiveType === 'string' && /(^|-)2g$/.test(conn.effectiveType);
}

let precacheStarted = false;

export async function scheduleLexiconPrecache(): Promise<void> {
  if (precacheStarted || isMeteredConnection()) return;
  if (typeof navigator === 'undefined' || !navigator.onLine) return;
  precacheStarted = true;
  try {
    const target = await getCurrentLexiconTarget();
    const cache = await getLexiconCacheStatusSafe(target);
    if (cache.any) return;
    await fetch(target.fetchUrl, { priority: 'low' } as RequestInit);
  } catch {
    precacheStarted = false;
  }
}

async function getLexiconCacheStatusSafe(
  target: Awaited<ReturnType<typeof getCurrentLexiconTarget>>,
): Promise<{ any: boolean }> {
  const { getLexiconCacheStatus } = await import('./db/lexicon-restore.ts');
  return getLexiconCacheStatus(target);
}