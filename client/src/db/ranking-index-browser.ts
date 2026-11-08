import { publicAssetUrl } from './lexicon-manifest.ts';
import { initRankingData } from './ranking.ts';

let rankingLoaded = false;
const RANKING_CACHE = 'ranking-index-verified-v1';

/** Browser/worker shared loader: ranking state is realm-local, so each realm must initialise it. */
export async function loadBrowserRankingIndex(): Promise<void> {
  if (rankingLoaded) return;
  const dev = Boolean((import.meta as ImportMeta).env?.DEV);
  const fingerprint = (import.meta as ImportMeta).env?.VITE_RANKING_INDEX_SHA256 || '';
  try {
    if (!dev && !/^[a-f0-9]{64}$/.test(fingerprint)) throw new Error('Missing ranking index identity');
    const url = publicAssetUrl(fingerprint ? `ranking-index.${fingerprint}.json` : 'ranking-index.json');
    // Both window and OPFS worker use the same verified, immutable cache key.
    // Do not depend on a service worker already controlling the first visit.
    const cache = dev ? undefined : await caches.open(RANKING_CACHE);
    const cached = await cache?.match(url);
    const res = cached || await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Failed to load ranking index (${res.status})`);
    const saved = res.clone();
    let data;
    try {
      const bytes = await res.arrayBuffer();
      data = JSON.parse(new TextDecoder().decode(bytes));
      validateRankingIndex(data);
      if (fingerprint) {
        const digest = await crypto.subtle.digest('SHA-256', bytes);
        const actual = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
        if (actual !== fingerprint) throw new Error('Ranking index identity mismatch');
      }
    } catch (error) {
      if (cached) await cache?.delete(url);
      throw error;
    }
    // Persistence is part of readiness, not a background SWR update.
    if (cache && !cached) await cache.put(url, saved);
    initRankingData(data);
    rankingLoaded = true;
  } catch (error) {
    if (!dev) throw error;
    // Vite dev can run before generated ranking assets exist; remain retryable.
    console.warn('Ranking index unavailable in development:', error);
  }
}

function validateRankingIndex(data: any): void {
  if (
    !data?.essay || typeof data.essay !== 'object' || Array.isArray(data.essay) ||
    !Object.keys(data.essay).length || !Array.isArray(data.curated) ||
    !data.pronRank || typeof data.pronRank !== 'object' || Array.isArray(data.pronRank) ||
    !data.wordUsage || typeof data.wordUsage !== 'object' || Array.isArray(data.wordUsage) ||
    !Object.keys(data.wordUsage).length || Object.values(data.wordUsage).some(value =>
      !Array.isArray(value) || value.length !== 2 ||
      !Number.isInteger(value[0]) || value[0] < 0 || value[0] > 3 ||
      !Number.isSafeInteger(value[1]) || value[1] < 0)
  ) {
    throw new Error('Invalid ranking index');
  }
}

export function resetBrowserRankingIndex(): void {
  rankingLoaded = false;
}
