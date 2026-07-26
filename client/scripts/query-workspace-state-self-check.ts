import assert from 'node:assert/strict';

import {
  createInitialQueryWorkspaceState,
  reduceQueryWorkspace,
  snapshotFromQueryWorkspace,
  type QueryWorkspaceSnapshot,
} from '../src/query-workspace/state.ts';

type Row = { word: string };

const emptyFilter = { pos: [], family: [], voice: [] };
const firstSnapshot: QueryWorkspaceSnapshot<Row> = {
  tabId: 1,
  q: '香港',
  results: [{ word: '香港' }],
  offset: 1,
  total: 1,
  posFilter: emptyFilter,
};
const secondSnapshot: QueryWorkspaceSnapshot<Row> = {
  tabId: 2,
  q: '朋友',
  results: [{ word: '朋友' }],
  offset: 1,
  total: 1,
  posFilter: { pos: ['n'], family: [], voice: [] },
};

let state = createInitialQueryWorkspaceState<Row>();
state = reduceQueryWorkspace(state, { type: 'activateTab', snapshot: firstSnapshot });
assert.equal(state.tabId, 1);
assert.equal(state.draftQuery, '香港');
assert.deepEqual(state.results, firstSnapshot.results);

state = reduceQueryWorkspace(state, {
  type: 'beginFrame',
  query: '香港',
  mode: 'm1',
  pzmode: 'm1',
  kind: 'commit',
});
const firstFrameId = state.activeFrameId;
assert.ok(firstFrameId != null);

state = reduceQueryWorkspace(state, {
  type: 'requestStarted',
  frameId: firstFrameId,
  requestId: 11,
  append: false,
});
state = reduceQueryWorkspace(state, {
  type: 'beginFrame',
  query: '朋友',
  mode: 'm1',
  pzmode: 'm1',
  kind: 'preview',
});
const secondFrameId = state.activeFrameId;
assert.ok(secondFrameId != null && secondFrameId !== firstFrameId);

state = reduceQueryWorkspace(state, {
  type: 'requestResolved',
  frameId: firstFrameId,
  requestId: 11,
  items: [{ word: '過期結果' }],
  total: 1,
  append: false,
});
assert.deepEqual(state.results, firstSnapshot.results);
assert.equal(state.status, 'previewing');

state = reduceQueryWorkspace(state, {
  type: 'requestStarted',
  frameId: secondFrameId!,
  requestId: 12,
  append: false,
});
state = reduceQueryWorkspace(state, {
  type: 'requestResolved',
  frameId: secondFrameId!,
  requestId: 12,
  items: [{ word: '朋友' }],
  total: 1,
  append: false,
});
assert.deepEqual(state.results, [{ word: '朋友' }]);
assert.equal(state.status, 'ready');

state = reduceQueryWorkspace(state, { type: 'activateTab', snapshot: secondSnapshot });
assert.equal(state.tabId, 2);
assert.equal(state.draftQuery, '朋友');
assert.deepEqual(snapshotFromQueryWorkspace(state), secondSnapshot);

state = reduceQueryWorkspace(state, { type: 'leave' });
assert.equal(state.tabId, null);
assert.equal(state.activeFrameId, null);
assert.equal(state.status, 'idle');

console.log('query-workspace-state self-check ok');
