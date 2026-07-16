import { VIEW } from "./query-tabs-state.mjs";
import { commitSearchHistoryFrame } from "./search-navigation.mjs";

function cloneSearchTab(tab) {
  return {
    ...tab,
    historyStack: tab.historyStack?.map((frame) => ({ ...frame })),
  };
}

export function commitActiveSearchTransaction(state, frame) {
  const active = state.tabs.find((tab) => tab.id === state.activeId);
  if (!active || active.view !== VIEW.SEARCH) {
    return { state, pushed: false };
  }

  const nextTab = cloneSearchTab(active);
  const { pushed } = commitSearchHistoryFrame(nextTab, frame);
  return {
    state: {
      ...state,
      tabs: state.tabs.map((tab) => (tab.id === nextTab.id ? nextTab : tab)),
    },
    pushed,
  };
}

export function openCommittedSearchTabTransaction(state, frame, createSearchTab) {
  const tab = createSearchTab({ id: state.nextTabId });
  const { pushed } = commitSearchHistoryFrame(tab, frame);
  return {
    state: {
      activeId: tab.id,
      nextTabId: state.nextTabId + 1,
      tabs: [...state.tabs, tab],
    },
    pushed,
  };
}
