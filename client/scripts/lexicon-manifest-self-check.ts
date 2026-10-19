/** ADR-0032 G: manifest gzip target resolution */
import {
  buildDevLexiconTarget,
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
