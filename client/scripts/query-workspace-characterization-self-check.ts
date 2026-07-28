import assert from 'node:assert/strict';

import {
  createInitialQueryWorkspaceState,
  reduceQueryWorkspace,
  snapshotFromQueryWorkspace,
  type QueryWorkspaceSnapshot,
} from '../src/query-workspace/state.ts';

type Row = { word: string };

const emptyFilter = { pos: [], family: [], voice: [] };
const tabA: QueryWorkspaceSnapshot<Row> = {
  tabId: 1,
  q: '香港',
  results: [{ word: '香港' }],
  offset: 1,
  total: 2,
  mode: 'm1',
  pzmode: 'm1',
  shuffled: false,
  scrollTop: 0,
  dataVersion: 'test',
  posFilter: emptyFilter,
};
const tabB: QueryWorkspaceSnapshot<Row> = {
  tabId: 2,
  q: '朋友',
  results: [{ word: '朋友' }],
  offset: 1,
  total: 1,
  mode: 'm1',
  pzmode: 'm1',
  shuffled: false,
  scrollTop: 0,
  dataVersion: 'test',
  posFilter: { pos: ['n'], family: [], voice: [] },
};

let state = createInitialQueryWorkspaceState<Row>();
state = reduceQueryWorkspace(state, { type: 'activateTab', snapshot: tabA });
state = reduceQueryWorkspace(state, {
  type: 'beginFrame',
  query: '香港',
  mode: 'm1',
  pzmode: 'm1',
  kind: 'commit',
});
const frameA = state.activeFrameId;
assert.ok(frameA != null);

state = reduceQueryWorkspace(state, {
  type: 'requestStarted',
  frameId: frameA,
  requestId: 1,
  append: false,
});
state = reduceQueryWorkspace(state, {
  type: 'requestResolved',
  frameId: frameA,
  requestId: 1,
  items: [{ word: '香港' }],
  total: 2,
  append: false,
});
assert.equal(state.status, 'ready');
assert.deepEqual(snapshotFromQueryWorkspace(state), tabA);

state = reduceQueryWorkspace(state, {
  type: 'requestStarted',
  frameId: frameA,
  requestId: 2,
  append: true,
});
state = reduceQueryWorkspace(state, {
  type: 'activateTab',
  snapshot: tabB,
});
assert.equal(state.tabId, 2);
assert.deepEqual(state.results, tabB.results);
assert.deepEqual(state.posFilter, tabB.posFilter);

state = reduceQueryWorkspace(state, {
  type: 'requestResolved',
  frameId: frameA,
  requestId: 2,
  items: [{ word: '不應串頁' }],
  total: 2,
  append: true,
});
assert.deepEqual(state.results, tabB.results);
assert.equal(state.status, 'ready');

state = reduceQueryWorkspace(state, {
  type: 'beginFrame',
  query: '朋友',
  mode: 'm1',
  pzmode: 'm1',
  kind: 'preview',
});
const previewFrame = state.activeFrameId;
assert.ok(previewFrame != null);
state = reduceQueryWorkspace(state, {
  type: 'requestStarted',
  frameId: previewFrame,
  requestId: 3,
  append: false,
});
state = reduceQueryWorkspace(state, {
  type: 'requestRejected',
  frameId: previewFrame,
  requestId: 3,
  message: 'preview failed',
});
assert.equal(state.status, 'error');
assert.equal(state.error, 'preview failed');
assert.deepEqual(state.results, tabB.results);

state = reduceQueryWorkspace(state, { type: 'activateTab', snapshot: tabA });
assert.deepEqual(snapshotFromQueryWorkspace(state), tabA);

console.log('query-workspace-characterization self-check ok');
