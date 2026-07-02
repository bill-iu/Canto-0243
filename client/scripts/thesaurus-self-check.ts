/** ponytail: static syn index build smoke test */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildStaticSynIndex } from '../src/db/thesaurus-loader.node.ts';
import { getStaticSynonyms, initStaticSynIndex } from '../src/db/thesaurus.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const index = buildStaticSynIndex(repoRoot);
if (!Object.keys(index).length) {
  throw new Error('thesaurus-self-check: empty index (run bootstrap_data?)');
}
initStaticSynIndex(index);
const syns = getStaticSynonyms('開');
if (!syns.length) {
  throw new Error('thesaurus-self-check: 開 has no static syns');
}
console.log('thesaurus self-check ok');
