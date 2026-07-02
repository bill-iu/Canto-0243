/** ponytail: parser classification self-check for P1 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { parserLogicSelfCheck } from '../src/db/query-engine.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);

parserLogicSelfCheck();
console.log('parser self-check ok');
