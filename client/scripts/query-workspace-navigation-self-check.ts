import assert from 'node:assert/strict';

import {
  createMemoryNavigationAdapter,
  type QueryWorkspaceCommittedFrame,
} from '../src/query-workspace/navigation-adapter.ts';

const { adapter, frames, checkpoints } = createMemoryNavigationAdapter();
const frame: QueryWorkspaceCommittedFrame = {
  query: '香港',
  mode: '0243',
  pzmode: 'm1',
  fallback0243Mode: '0243',
};

adapter.commit(frame);
assert.deepEqual(frames, [frame]);
frame.query = '不應回寫';
assert.equal(frames[0]?.query, '香港');

adapter.checkpoint(3, {
  tabId: 3,
  q: '朋友',
  results: [{ word: '朋友' }],
  offset: 1,
  total: 1,
  posFilter: { pos: [], family: [], voice: [] },
});
assert.equal(checkpoints[0]?.tabId, 3);
assert.deepEqual(checkpoints[0]?.snapshot.results, [{ word: '朋友' }]);

console.log('query-workspace-navigation self-check ok');
