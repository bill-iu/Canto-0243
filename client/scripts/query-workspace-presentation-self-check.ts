import assert from 'node:assert/strict';

import { mergeShuffledResults } from '../src/shuffle-results.ts';
import { buildPresentationCheckpoint } from '../src/query-workspace/presentation.ts';

type Row = { word: string };

const original = [
  { word: 'a' },
  { word: 'b' },
  { word: 'c' },
] as Row[];
const shuffled = [original[2], original[0], original[1]];

assert.deepEqual(
  mergeShuffledResults(shuffled as never[], original as never[]),
  shuffled,
  'shuffle presentation must not be replaced by the unshuffled page when lengths match',
);

const firstTab = {
  tabId: 1,
  q: 'first',
  results: [{ word: 'first' }] as Row[],
  offset: 1,
  total: 1,
  posFilter: { pos: [], family: [], voice: [] },
};
const secondTabResults = [{ word: 'second' }] as Row[];

assert.equal(
  buildPresentationCheckpoint(firstTab, 2, secondTabResults, true),
  null,
  'a stale presentation from another tab must not checkpoint into the active tab',
);

const checkpoint = buildPresentationCheckpoint(firstTab, 1, secondTabResults, false);
assert.deepEqual(checkpoint?.results, firstTab.results);
assert.equal(checkpoint?.offset, 1);

console.log('query-workspace-presentation self-check ok');
