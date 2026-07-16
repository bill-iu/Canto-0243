import { createSearchTab, VIEW } from '../../shared/query-tabs-state.mjs';
import {
  commitActiveSearchTransaction,
  openCommittedSearchTabTransaction,
} from '../../shared/committed-search.mjs';

function state() {
  return { activeId: 1, nextTabId: 2, tabs: [createSearchTab({ id: 1 })] };
}

const basic = commitActiveSearchTransaction(state(), { q: '香港', mode: 'm1', pzmode: 'm1' });
if (!basic.pushed || basic.state.tabs[0]?.historyStack?.[1]?.mode !== 'm1') {
  throw new Error('committed-search: basic frame missing');
}

for (const pzmode of ['m1', 'm2', 'm3']) {
  const transaction = commitActiveSearchTransaction(state(), { q: 'PZ?', mode: 'pz', pzmode });
  const frame = transaction.state.tabs[0]?.historyStack?.[1];
  if (!transaction.pushed || frame?.mode !== 'pz' || frame.pzmode !== pzmode) {
    throw new Error(`committed-search: pingze ${pzmode} frame missing`);
  }
}

const duplicate = commitActiveSearchTransaction(basic.state, { q: '香港', mode: 'm1', pzmode: 'm1' });
if (duplicate.pushed || duplicate.state.tabs[0]?.historyStack?.length !== 2) {
  throw new Error('committed-search: duplicate frame must replace');
}

const synonym = commitActiveSearchTransaction(state(), { q: '開心', mode: 'syn', pzmode: 'm1' });
if (synonym.state.tabs[0]?.historyStack?.[1]?.mode !== 'syn') {
  throw new Error('committed-search: synonym frame missing');
}

const guide = openCommittedSearchTabTransaction(state(), { q: 'PZ?', mode: 'pz', pzmode: 'm3' }, createSearchTab);
const guideTab = guide.state.tabs[1];
if (guide.state.activeId !== 2 || guideTab?.view !== VIEW.SEARCH || guideTab.historyStack?.[1]?.pzmode !== 'm3') {
  throw new Error('committed-search: guide tab frame missing');
}

console.log('committed-search self-check ok');
