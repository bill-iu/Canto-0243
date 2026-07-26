import assert from 'node:assert/strict';

import {
  createMemoryNavigationAdapter,
  type QueryWorkspaceCommittedFrame,
} from '../src/query-workspace/navigation-adapter.ts';

const { adapter, frames } = createMemoryNavigationAdapter();
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

console.log('query-workspace-navigation self-check ok');
