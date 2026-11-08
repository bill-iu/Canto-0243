/** ADR-0032 G: manifest gzip target resolution */
import {
  buildDevLexiconTarget,
  loadLexiconTarget,
  lexiconStorageVersion,
  resolveTargetFromManifest,
  type LexiconManifest,
} from '../src/db/lexicon-manifest.ts';

const plain: LexiconManifest = {
  lexiconVersion: 'dev',
  dbFile: 'lyrics.dev.db',
  byteSize: 100,
  sha256: 'abc',
  preferCompressed: false,
};
const plainTarget = resolveTargetFromManifest(plain, 'dev');
if (plainTarget.useGzip || plainTarget.fetchUrl !== plainTarget.dbUrl) {
  throw new Error('lexicon-manifest-self-check: plain target');
}

const gz: LexiconManifest = {
  lexiconVersion: '394052',
  dbFile: 'lyrics.394052.db',
  dbFileGz: 'lyrics.394052.db.gz',
  byteSize: 1000,
  compressedByteSize: 300,
  sha256: 'def',
  preferCompressed: true,
};
const gzTarget = resolveTargetFromManifest(gz, '394052');
if (!gzTarget.useGzip || gzTarget.fetchByteSize !== 300) {
  throw new Error('lexicon-manifest-self-check: gzip target');
}
if (!new URL(gzTarget.fetchUrl, 'https://example.test').pathname.endsWith('.db.gz')) {
  throw new Error('lexicon-manifest-self-check: gzip fetchUrl');
}

const devT = buildDevLexiconTarget('v1.0.7', 39092224);
if (devT.version !== 'v1.0.7-dev-39092224' || devT.byteSize != null || devT.useGzip) {
  throw new Error('lexicon-manifest-self-check: buildDevLexiconTarget');
}
if (buildDevLexiconTarget('v1').version !== 'v1-dev') {
  throw new Error('lexicon-manifest-self-check: buildDevLexiconTarget no size');
}

console.log('lexicon-manifest self-check ok');

// Regression: refreshed v1.1.2 has different content but exactly the same byte size.
const oldSnapshot = resolveTargetFromManifest({ ...gz, lexiconVersion: 'v1.1.2', sha256: 'a'.repeat(64) }, 'v1.1.2');
const newSnapshot = resolveTargetFromManifest({ ...gz, lexiconVersion: 'v1.1.2', sha256: 'b'.repeat(64) }, 'v1.1.2');
if (oldSnapshot.version !== newSnapshot.version || oldSnapshot.byteSize !== newSnapshot.byteSize) {
  throw new Error('same-tag replacement fixture must keep its version and size');
}
if (lexiconStorageVersion(oldSnapshot) === lexiconStorageVersion(newSnapshot)
  || oldSnapshot.fetchUrl === newSnapshot.fetchUrl || oldSnapshot.dbUrl === newSnapshot.dbUrl) {
  throw new Error('same-tag replacement must miss both OPFS and SW caches');
}
if (lexiconStorageVersion({ version: 'legacy' }) !== 'legacy') {
  throw new Error('manifest without a fingerprint must preserve its legacy cache key');
}

// First visit can finish before SW control; a subsequent offline cold start
// must retain the exact DB identity, not fall back to an unhashed filename.
const originalFetch = globalThis.fetch;
const originalCaches = Object.getOwnPropertyDescriptor(globalThis, 'caches');
let stored: Response | undefined;
let failPut = false;
const offline = async (): Promise<Response> => { throw new TypeError('offline'); };
const latest = { ...gz, lexiconVersion: 'v1.1.2', sha256: 'b'.repeat(64) };
try {
  Object.defineProperty(globalThis, 'caches', { configurable: true, value: {
    async open(name: string) {
      if (name !== 'lexicon-manifest-cache') throw new Error('wrong cache');
      return {
        async match() { return stored?.clone(); },
        async put(_url: string, response: Response) {
          if (failPut) throw new Error('quota failure');
          stored = response.clone();
        },
      };
    },
  } });
  globalThis.fetch = async () => Response.json(latest);
  const online = await loadLexiconTarget();
  if (!stored || online.sha256 !== latest.sha256) throw new Error('first manifest not persisted');
  globalThis.fetch = offline;
  const cached = await loadLexiconTarget();
  if (JSON.stringify(cached) !== JSON.stringify(online)) throw new Error('offline DB identity changed');
  const refresh = { ...latest, sha256: 'c'.repeat(64) };
  globalThis.fetch = async () => Response.json(refresh);
  const updated = await loadLexiconTarget();
  if (updated.sha256 !== refresh.sha256 || updated.fetchUrl === online.fetchUrl) {
    throw new Error('same-tag network update must replace the old manifest');
  }
  globalThis.fetch = offline;
  if ((await loadLexiconTarget()).sha256 !== refresh.sha256) throw new Error('offline refresh missing');
  failPut = true;
  globalThis.fetch = async () => Response.json(latest);
  let rejected = false;
  try { await loadLexiconTarget(); } catch { rejected = true; }
  if (!rejected) throw new Error('storage failure must not silently change DB identity');
} finally {
  globalThis.fetch = originalFetch;
  if (originalCaches) Object.defineProperty(globalThis, 'caches', originalCaches);
  else Reflect.deleteProperty(globalThis, 'caches');
}
console.log('lexicon manifest first-visit offline identity and same-tag refresh ok');
