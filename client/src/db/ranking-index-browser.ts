import { publicAssetUrl } from './lexicon-manifest.ts';
import { initRankingData } from './ranking.ts';

let rankingLoaded = false;

/** Browser/worker shared loader: ranking state is realm-local, so each realm must initialise it. */
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

export function resetBrowserRankingIndex(): void {
  rankingLoaded = false;
}
