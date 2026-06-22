/** Result click + per-tab search history (testable without DOM). */
import { VIEW, buildUrlSearchParams } from "./query-tabs-state.mjs";

function blankHistoryFrame(mode = "m1") {
  return { q: "", mode };
}

function ensureSearchTabHistory(tab, defaultMode = "m1") {
  if (tab.view !== VIEW.SEARCH) return tab;
  if (!Array.isArray(tab.historyStack) || !tab.historyStack.length) {
    const stack = [blankHistoryFrame(defaultMode)];
    if ((tab.q || "").trim()) stack.push({ q: tab.q.trim(), mode: defaultMode });
    tab.historyStack = stack;
    tab.historyIndex = stack.length - 1;
  }
  if (typeof tab.historyIndex !== "number") tab.historyIndex = tab.historyStack.length - 1;
  return tab;
}

function currentSearchHistoryFrame(tab) {
  ensureSearchTabHistory(tab);
  return tab.historyStack[tab.historyIndex];
}

function commitSearchHistoryFrame(tab, { q, mode }) {
  ensureSearchTabHistory(tab, mode);
  const frame = { q, mode };
  const current = tab.historyStack[tab.historyIndex];
  if (current.q === frame.q && current.mode === frame.mode) {
    tab.q = frame.q;
    return { pushed: false, frame: current };
  }
  tab.historyStack = tab.historyStack.slice(0, tab.historyIndex + 1);
  tab.historyStack.push(frame);
  tab.historyIndex = tab.historyStack.length - 1;
  tab.q = frame.q;
  return { pushed: true, frame };
}

function stepSearchTabBack(tab) {
  ensureSearchTabHistory(tab);
  if (tab.historyIndex <= 0) return null;
  tab.historyIndex -= 1;
  const frame = tab.historyStack[tab.historyIndex];
  tab.q = frame.q;
  return frame;
}

function isHistoryForward(lastSeq, state) {
  const seq = state?._histSeq;
  if (typeof seq !== "number") return false;
  return seq > (lastSeq ?? 0);
}

function applyPopstateToSearchTab(tab, _state) {
  return stepSearchTabBack(tab) ?? currentSearchHistoryFrame(tab);
}

function shouldApplySearchPopstate(activeTab, state) {
  if (!activeTab || activeTab.view !== VIEW.SEARCH) return false;
  if (!state?.tabId || state.tabId !== activeTab.id) return false;
  if (state.view && state.view !== VIEW.SEARCH) return false;
  return true;
}

function resetSearchTabHistory(tab, mode = "m1") {
  if (tab.view !== VIEW.SEARCH) return tab;
  tab.historyStack = [blankHistoryFrame(mode)];
  tab.historyIndex = 0;
  tab.q = "";
  tab.results = [];
  tab.offset = 0;
  tab.total = null;
  return tab;
}

function withResultClickQuery(tab, queryText) {
  return { ...tab, q: queryText };
}

function shouldPushSearchHistory(next, prev) {
  if (!prev || !next) return true;
  return !(
    prev.tabId === next.tabId
    && prev.view === next.view
    && (prev.query || "") === (next.query || "")
    && (prev.mode || "m1") === (next.mode || "m1")
  );
}

function buildHistoryStateForTab(tab, mode = "m1") {
  if (tab.view === VIEW.SEARCH) {
    const frame = currentSearchHistoryFrame(tab);
    return {
      tabId: tab.id,
      view: tab.view,
      query: frame.q,
      mode: frame.mode,
    };
  }
  return {
    tabId: tab.id,
    view: tab.view,
    query: "",
    mode,
  };
}

function buildResultSearchHref({ pathname, query, mode }) {
  const params = buildUrlSearchParams({ view: VIEW.SEARCH, q: query }, mode);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return `${pathname}${suffix}`;
}

function resolveSearchRestore(cache, cacheKey) {
  if (cache.has(cacheKey)) {
    return { source: "cache", entry: cache.get(cacheKey) };
  }
  return { source: "fetch" };
}

export {
  applyPopstateToSearchTab,
  buildHistoryStateForTab,
  buildResultSearchHref,
  commitSearchHistoryFrame,
  currentSearchHistoryFrame,
  ensureSearchTabHistory,
  isHistoryForward,
  resetSearchTabHistory,
  resolveSearchRestore,
  shouldApplySearchPopstate,
  shouldPushSearchHistory,
  stepSearchTabBack,
  withResultClickQuery,
};