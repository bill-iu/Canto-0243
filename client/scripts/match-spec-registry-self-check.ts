/** ponytail: MF-2 MatchSpec registry parity — MATCH_SPEC_REPRESENTATIVE_CASES */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { normalizeAndParse } from '../src/db/query-engine.ts';
import {
  buildMatchSpecForParsed,
  validateRepresentativeMatchSpec,
} from '../src/db/position-match/match-spec-registry.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);

const cases: Array<[string, Record<string, unknown>]> = [
  ['香港=', { width: 2, ref_literal: '香港', whole_word: true }],
  ['?困潦倒=', { width: 4, prefix_wildcard: true }],
  ['04困=49倒=', { width: 4, anchor_count: 2 }],
  ['23+就', { width: 3, code_prefix: '23' }],
  ['23@就', { width: 2, mask: '?就' }],
  ['就=', { width: 1, anchor: '就' }],
  ['?yut?', { width: 3, jyutping_slot: true }],
  ['3m4', { width: 2, dual_phoneme: true }],
  ['23就', { width: 2, hybrid_ref: '就' }],
  ['門0', { width: 2, literal_priority: true }],
  ['33~~你', { width: 2, compound_kind: 'syn', code_prefix: '33' }],
  ['$$', { width: 2, compound_kind: 'doubled_syllable' }],
  ['33!!你', { width: 2, compound_kind: 'ant', code_prefix: '33' }],
  ['窮?潦倒=', { width: 4, partial_rhyme_mask: true, anchor_count: 3 }],
  ['=窮?潦倒', { width: 4, partial_initial_mask: true, anchor_count: 3 }],
];

for (const [q, expected] of cases) {
  const spec = buildMatchSpecForParsed(normalizeAndParse(q));
  validateRepresentativeMatchSpec(q, spec, expected);
}

console.log('match-spec registry self-check ok');
