/**
 * DB-4 lexicon dual-path restore — OPFS first, then SW CacheFirst / network
 * ADR-0024 §7.2 DB-4; contract: specs/001-pwa-offline-coexist/contracts/offline-readiness.md
 */
import { lexiconOpfsFileName, readLexiconFromOpfs } from './opfs-lexicon.ts';
import { opfsFileSize } from './opfs-storage.ts';

export type LexiconRestoreSource = 'opfs' | 'sw-cache' | 'network';

export type LexiconCacheStatus = {
  opfs: boolean;
  swCache: boolean;
  /** true when either local copy exists (offline init may succeed) */
  any: boolean;
};

export async function isOpfsLexiconCached(version: string): Promise<boolean> {
  return (await opfsFileSize(lexiconOpfsFileName(version))) > 0;
}

export async function isSwLexiconCached(dbUrl: string): Promise<boolean> {
  if (!('caches' in globalThis)) {
    return false;
  }
  try {
    return Boolean(await caches.match(dbUrl));
  } catch {
    return false;
  }
}

export async function getLexiconCacheStatus(
  version: string,
  dbUrl: string,
): Promise<LexiconCacheStatus> {
  const [opfs, swCache] = await Promise.all([
    isOpfsLexiconCached(version),
    isSwLexiconCached(dbUrl),
  ]);
  return { opfs, swCache, any: opfs || swCache };
}

/** @deprecated use getLexiconCacheStatus().any */
export async function isLexiconCachedAnywhere(version: string, dbUrl: string): Promise<boolean> {
  return (await getLexiconCacheStatus(version, dbUrl)).any;
}

async function fetchLexiconFromUrl(dbUrl: string): Promise<Uint8Array> {
  const response = await fetch(dbUrl);
  if (!response.ok) {
    throw new Error(`Failed to fetch lexicon package (${response.status})`);
  }
  return new Uint8Array(await response.arrayBuffer());
}

/**
 * Restore lexicon bytes: OPFS → fetch (SW CacheFirst when installed, else network).
 * ponytail: fetch cannot distinguish SW vs network; use hadSwCache + navigator.onLine heuristic.
 */
export async function resolveLexiconBytes(
  version: string,
  dbUrl: string,
): Promise<{ bytes: Uint8Array; source: LexiconRestoreSource }> {
  const fromOpfs = await readLexiconFromOpfs(version);
  if (fromOpfs?.byteLength) {
    return { bytes: fromOpfs, source: 'opfs' };
  }

  const hadSwCache = await isSwLexiconCached(dbUrl);
  const bytes = await fetchLexiconFromUrl(dbUrl);
  const offline = typeof navigator !== 'undefined' && !navigator.onLine;
  const source: LexiconRestoreSource =
    hadSwCache || (offline && bytes.byteLength > 0) ? 'sw-cache' : 'network';
  return { bytes, source };
}
