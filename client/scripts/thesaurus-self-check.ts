/** ponytail: static syn/ant index build smoke test */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildStaticAntIndex,
  buildStaticSynIndex,
} from '../src/db/thesaurus-loader.node.ts';
import {
  getStaticAntonyms,
  getStaticSynonyms,
  initStaticAntIndex,
  initStaticSynIndex,
} from '../src/db/thesaurus.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const synIndex = buildStaticSynIndex(repoRoot);
if (!Object.keys(synIndex).length) {
  throw new Error('thesaurus-self-check: empty syn index (run bootstrap_data?)');
}
initStaticSynIndex(synIndex);
const syns = getStaticSynonyms('開');
if (!syns.length) {
  throw new Error('thesaurus-self-check: 開 has no static syns');
}

const antIndex = buildStaticAntIndex(repoRoot);
initStaticAntIndex(antIndex);
// dict_antonym.txt majority separator is ASCII `--` (e.g. 死--活)
const ants = getStaticAntonyms('死');
if (!ants.includes('活')) {
  throw new Error(`thesaurus-self-check: 死 missing 活 antonym (got ${ants.join(',')})`);
}
console.log('thesaurus self-check ok');
