/**
 * DB-4 lexicon dual-path restore — OPFS first, then SW CacheFirst / network
 * ADR-0024 §7.2 DB-4; contract: specs/001-pwa-offline-coexist/contracts/offline-readiness.md
 */
import { lexiconOpfsFileName, readLexiconFromOpfs, removeLexiconFromOpfs } from './opfs-lexicon.ts';
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
  // Use Web Locks to serialise concurrent downloads across tabs.
  // The tab that wins the lock fetches once; the SW CacheFirst strategy caches the
  // response. Subsequent tabs that acquire the lock call fetch() and are served
  // instantly from SW cache — no additional network request.
  const doFetch = async (): Promise<Uint8Array> => {
    const response = await fetch(dbUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch lexicon package (${response.status})`);
    }
    return new Uint8Array(await response.arrayBuffer());
  };

  if (typeof navigator !== 'undefined' && 'locks' in navigator) {
    const safeName = dbUrl.replace(/[^a-zA-Z0-9._-]+/g, '_').slice(-80);
    return (navigator as Navigator & { locks: LockManager }).locks.request(
      `lexicon-fetch-${safeName}`,
      doFetch,
    );
  }
  return doFetch();
}

/**
 * Restore lexicon bytes: OPFS → fetch (SW CacheFirst when installed, else network).
 * ponytail: fetch cannot distinguish SW vs network; use hadSwCache + navigator.onLine heuristic.
 */
export type LexiconIntegrity = {
  byteSize?: number;
  sha256?: string;
};

async function purgeBadOpfsLexicon(
  version: string,
  bytes: Uint8Array | null,
  expected?: LexiconIntegrity,
): Promise<void> {
  if (!bytes?.byteLength || expected?.byteSize == null) {
    return;
  }
  if (bytes.byteLength !== expected.byteSize) {
    console.warn(
      `OPFS lexicon size mismatch (${bytes.byteLength} vs ${expected.byteSize}); purging stale copy`,
    );
    await removeLexiconFromOpfs(version);
  }
}

export async function resolveLexiconBytes(
  version: string,
  dbUrl: string,
  expected?: LexiconIntegrity,
): Promise<{ bytes: Uint8Array; source: LexiconRestoreSource }> {
  const fromOpfs = await readLexiconFromOpfs(version);
  if (fromOpfs?.byteLength) {
    if (expected?.byteSize != null && fromOpfs.byteLength !== expected.byteSize) {
      await purgeBadOpfsLexicon(version, fromOpfs, expected);
    } else {
      return { bytes: fromOpfs, source: 'opfs' };
    }
  }

  const offline = typeof navigator !== 'undefined' && !navigator.onLine;
  const hadSwCache = await isSwLexiconCached(dbUrl);
  if (offline && !hadSwCache) {
    throw new Error('Lexicon not cached for offline use (OPFS and SW both missing)');
  }
  const bytes = await fetchLexiconFromUrl(dbUrl);
  if (expected?.byteSize != null && bytes.byteLength !== expected.byteSize) {
    throw new Error(
      `Lexicon size mismatch after fetch: expected ${expected.byteSize} bytes, got ${bytes.byteLength}`,
    );
  }
  const source: LexiconRestoreSource =
    hadSwCache || (offline && bytes.byteLength > 0) ? 'sw-cache' : 'network';
  return { bytes, source };
}
