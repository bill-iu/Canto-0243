import assert from 'node:assert/strict';

import {
  createMemoryNavigationAdapter,
  createCallbackNavigationAdapter,
  commitReadyPreview,
  type QueryWorkspaceCommittedFrame,
} from '../src/query-workspace/navigation-adapter.ts';
import { createInitialQueryWorkspaceState, reduceQueryWorkspace } from '../src/query-workspace/state.ts';
import { createSearchTab } from '../../shared/query-tabs-state.mjs';
import { commitActiveSearchTransaction } from '../../shared/committed-search.mjs';
import { stepSearchTabBack } from '../../shared/search-navigation.mjs';

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

// Automatic searches, without Enter: only completed results of the active app tab commit.
let tabs = { activeId: 1, nextTabId: 3, tabs: [createSearchTab({ id: 1 }), createSearchTab({ id: 2, q: '香港' })] };
const otherTab = structuredClone(tabs.tabs[1]);
const navigation = createCallbackNavigationAdapter({
  commitFrame: (next) => {
    tabs = commitActiveSearchTransaction(tabs, { q: next.query, mode: 'm1' }).state;
  },
  checkpoint: () => {},
});
function readyPreview(query: string) {
  let workspace = reduceQueryWorkspace(createInitialQueryWorkspaceState(), {
    type: 'activateTab',
    snapshot: { tabId: 1, q: '', results: [], offset: 0, total: null, posFilter: { pos: [], family: [], voice: [] } },
  });
  workspace = reduceQueryWorkspace(workspace, { type: 'beginFrame', query, mode: '0243', pzmode: 'm1', kind: 'preview' });
  const frameId = workspace.activeFrameId!;
  workspace = reduceQueryWorkspace(workspace, { type: 'requestStarted', frameId, requestId: 1, append: false });
  workspace = reduceQueryWorkspace(workspace, { type: 'requestResolved', frameId, requestId: 1, items: [], total: 0, append: false });
  return workspace;
}
const previous = readyPreview('43');
const latest = readyPreview('243');
commitReadyPreview(navigation, previous, 1);
commitReadyPreview(navigation, latest, 1);
commitReadyPreview(navigation, latest, 1);
assert.deepEqual(tabs.tabs[0].historyStack.map((entry: { q: string }) => entry.q), ['', '43', '243']);
assert.equal(stepSearchTabBack(tabs.tabs[0])?.q, '43');
assert.deepEqual(tabs.tabs[1], otherTab);
const beforeIgnored = structuredClone(tabs);
commitReadyPreview(navigation, latest, 2); // result arrives after switching app tab
commitReadyPreview(navigation, { ...latest, status: 'loading' }, 1);
commitReadyPreview(navigation, { ...latest, status: 'error' }, 1);
commitReadyPreview(navigation, { ...latest, activeFrame: null }, 1); // cached tab activation
assert.deepEqual(tabs, beforeIgnored);

console.log('query-workspace-navigation self-check ok');
