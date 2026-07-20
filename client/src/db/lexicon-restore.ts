/**
 * DB-4 lexicon dual-path restore — OPFS first, then SW CacheFirst / network
 */
import type { LexiconTarget } from './lexicon-manifest.ts';
import { fetchLexiconBytesFromUrl } from './lexicon-fetch.ts';
import { lexiconOpfsFileName, readLexiconFromOpfs, removeLexiconFromOpfs } from './opfs-lexicon.ts';
import { opfsFileSize } from './opfs-storage.ts';

export type LexiconRestoreSource = 'opfs' | 'sw-cache' | 'network';

export type LexiconCacheStatus = {
  opfs: boolean;
  swCache: boolean;
  any: boolean;
};

export async function isOpfsLexiconCached(version: string): Promise<boolean> {
  return (await opfsFileSize(lexiconOpfsFileName(version))) > 0;
}

export async function isSwLexiconCached(url: string): Promise<boolean> {
  if (!('caches' in globalThis)) return false;
  try {
    return Boolean(await caches.match(url));
  } catch {
    return false;
  }
}

/** C1 / ADR-0036: fixed-URL CacheFirst — drop stale SW db entries after integrity fail */
export async function purgeSwLexiconCache(urls: string[]): Promise<void> {
  if (!('caches' in globalThis)) return;
  try {
    const keys = await caches.keys();
    const dbCaches = keys.filter((k) => k.includes('database-cache') || k.includes('workbox'));
    for (const name of dbCaches) {
      const cache = await caches.open(name);
      for (const url of urls) {
        try {
          await cache.delete(url, { ignoreSearch: true });
        } catch {
          /* best-effort */
        }
      }
    }
  } catch {
    /* best-effort */
  }
}

export async function getLexiconCacheStatus(target: LexiconTarget): Promise<LexiconCacheStatus> {
  const [opfs, swFetch, swPlain] = await Promise.all([
    isOpfsLexiconCached(target.version),
    isSwLexiconCached(target.fetchUrl),
    target.fetchUrl !== target.dbUrl ? isSwLexiconCached(target.dbUrl) : Promise.resolve(false),
  ]);
  const swCache = swFetch || swPlain;
  return { opfs, swCache, any: opfs || swCache };
}

export type LexiconIntegrity = {
  byteSize?: number;
  sha256?: string;
};

async function purgeBadOpfsLexicon(
  version: string,
  bytes: Uint8Array | null,
  expected?: LexiconIntegrity,
): Promise<void> {
  if (!bytes?.byteLength || expected?.byteSize == null) return;
  if (bytes.byteLength !== expected.byteSize) {
    console.warn(
      `OPFS lexicon size mismatch (${bytes.byteLength} vs ${expected.byteSize}); purging stale copy`,
    );
    await removeLexiconFromOpfs(version);
  }
}

export async function purgeStaleLexiconCaches(
  target: LexiconTarget,
  reason: string,
): Promise<void> {
  console.warn(`Lexicon integrity: ${reason}; purging OPFS + SW database-cache`);
  try {
    await removeLexiconFromOpfs(target.version);
  } catch {
    /* best-effort */
  }
  const urls = [target.fetchUrl, target.dbUrl].filter(Boolean);
  await purgeSwLexiconCache([...new Set(urls)]);
}

async function fetchWithLock(fetchUrl: string, target: LexiconTarget): Promise<Uint8Array> {
  const run = () =>
    fetchLexiconBytesFromUrl(fetchUrl, {
      gzip: target.useGzip,
      progressTotal: target.fetchByteSize,
    });

  if (typeof navigator !== 'undefined' && 'locks' in navigator) {
    const safeName = fetchUrl.replace(/[^a-zA-Z0-9._-]+/g, '_').slice(-80);
    return (navigator as Navigator & { locks: LockManager }).locks.request(
      `lexicon-fetch-${safeName}`,
      run,
    );
  }
  return run();
}

export async function resolveLexiconBytes(
  target: LexiconTarget,
): Promise<{ bytes: Uint8Array; source: LexiconRestoreSource }> {
  const fromOpfs = await readLexiconFromOpfs(target.version);
  if (fromOpfs?.byteLength) {
    if (target.byteSize != null && fromOpfs.byteLength !== target.byteSize) {
      await purgeBadOpfsLexicon(target.version, fromOpfs, target);
      await purgeSwLexiconCache([target.fetchUrl, target.dbUrl].filter(Boolean));
    } else {
      return { bytes: fromOpfs, source: 'opfs' };
    }
  }

  const offline = typeof navigator !== 'undefined' && !navigator.onLine;
  const cache = await getLexiconCacheStatus(target);
  if (offline && !cache.any) {
    throw new Error('Lexicon not cached for offline use (OPFS and SW both missing)');
  }

  const hadSwCache = cache.swCache;
  const bytes = await fetchWithLock(target.fetchUrl, target);
  if (target.byteSize != null && bytes.byteLength !== target.byteSize) {
    await purgeStaleLexiconCaches(
      target,
      `fetch size ${bytes.byteLength} != ${target.byteSize}`,
    );
    throw new Error(
      `Lexicon size mismatch after fetch: expected ${target.byteSize} bytes, got ${bytes.byteLength}`,
    );
  }
  const source: LexiconRestoreSource =
    hadSwCache || (offline && bytes.byteLength > 0) ? 'sw-cache' : 'network';
  return { bytes, source };
}