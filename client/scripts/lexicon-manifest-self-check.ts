/** ADR-0032 G: manifest gzip target resolution */
import {
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
if (!gzTarget.fetchUrl.endsWith('.db.gz')) {
  throw new Error('lexicon-manifest-self-check: gzip fetchUrl');
}

console.log('lexicon-manifest self-check ok');