/** ponytail: jyutping rhyme_letters + rime index smoke test */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { jyutpingCodecSelfCheck } from '../src/db/jyutping-codec.ts';
import { classifyLatinAnchor, matchesJyutpingAnchorAtPosition } from '../src/db/jyutping-anchor.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import {
  rhymeLetterFinalOptions,
  rhymeLettersResolveOk,
  syllableMatchesRhymeFragment,
} from '../src/db/rime-index.ts';
import { parseJyutpingAnchorQuery } from '../src/db/query-engine.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);
jyutpingCodecSelfCheck();

if (!rhymeLettersResolveOk('o')) {
  throw new Error('jyutping-anchor-self-check: o not resolved');
}
if (!rhymeLettersResolveOk('ng')) {
  throw new Error('jyutping-anchor-self-check: ng not resolved');
}
if (!rhymeLettersResolveOk('yut')) {
  throw new Error('jyutping-anchor-self-check: yut not resolved');
}
if (classifyLatinAnchor('yut') !== 'rhyme_letters') {
  throw new Error('jyutping-anchor-self-check: yut should be rhyme_letters');
}
if (classifyLatinAnchor('ngo') !== 'syllable_letters') {
  throw new Error('jyutping-anchor-self-check: ngo should be syllable_letters');
}
if (!syllableMatchesRhymeFragment('jyut', 'yut')) {
  throw new Error('jyutping-anchor-self-check: jyut ends with yut');
}

const yutOpts = rhymeLetterFinalOptions('ut');
if (!yutOpts.size) {
  throw new Error('jyutping-anchor-self-check: ut options empty');
}

const parsed = parseJyutpingAnchorQuery('?yut?');
if (!parsed || parsed.anchor_kind !== 'rhyme_letters' || parsed.anchor_value !== 'yut') {
  throw new Error('jyutping-anchor-self-check: ?yut? parse');
}

const word = {
  jyutping: 'jyut6',
  finals: '["ut"]',
  initials: '["j"]',
};
if (!matchesJyutpingAnchorAtPosition(word, 0, 'rhyme_letters', 'yut')) {
  throw new Error('jyutping-anchor-self-check: yut rhyme match');
}
if (!matchesJyutpingAnchorAtPosition({ jyutping: 'ng5', finals: '[""]', initials: '["ng"]' }, 0, 'rhyme_letters', 'ng')) {
  throw new Error('jyutping-anchor-self-check: ng rhyme match');
}

console.log('jyutping-anchor self-check ok');
