/** ponytail: chrome-tabs id-order state — npx tsx scripts/chrome-tabs-bar-self-check.ts */
import {
  createSearchTab,
  reorderTabsByIds,
  type TabState,
} from '../../frontend/query-tabs-state.mjs';

const state: TabState = {
  activeId: 1,
  nextTabId: 4,
  tabs: [createSearchTab({ id: 1 }), createSearchTab({ id: 2 }), createSearchTab({ id: 3 })],
};

const moved = reorderTabsByIds(state, [3, 1, 2]);
if (moved.tabs.map((t) => t.id).join(',') !== '3,1,2') {
  throw new Error(`chrome-tabs-bar-self-check: got ${moved.tabs.map((t) => t.id)}`);
}
if (reorderTabsByIds(state, [1, 2, 3]) !== state) {
  throw new Error('chrome-tabs-bar-self-check: unchanged should be same ref');
}

console.log('chrome-tabs-bar-self-check: ok');
