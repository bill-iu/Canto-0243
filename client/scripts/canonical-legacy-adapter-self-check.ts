import assert from 'node:assert/strict';

import {
  canonicalMatchSpecToLegacy,
  canonicalizeLegacyMatchSpec,
  finalizeCanonicalMatchSpec,
} from '../src/db/position-match/canonical.ts';
import { getEqualsSpan } from '../src/db/position-match/spec.ts';

const canonical = finalizeCanonicalMatchSpec({
  width: 2,
  slots: [
    { pos: 0, kind: 'initial_anchor', value: new Set(['a', 'b']) },
  ],
  equals_span: {
    ref_literal: '香港',
    ref_jyutping: null,
    start_pos: 0,
    dimension: 'rhyme',
    phoneme_anchor_only: false,
    whole_word: false,
  },
});

const legacy = canonicalMatchSpecToLegacy(canonical);
const firstSlot = legacy.slots?.[0];
assert(firstSlot?.value instanceof Set);
assert.deepEqual([...firstSlot.value], ['a', 'b']);
assert.equal(getEqualsSpan(legacy)?.dimension, 'rhyme');

const roundTrip = canonicalizeLegacyMatchSpec(legacy);
assert.deepEqual(roundTrip.equals_span, canonical.equals_span);
assert.deepEqual(roundTrip.slots, canonical.slots);

console.log('canonical legacy adapter self-check ok');
