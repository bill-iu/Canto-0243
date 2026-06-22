/** Result click + browser history helpers (testable without DOM). */
import { VIEW, buildUrlSearchParams } from "./query-tabs-state.mjs";

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

function buildHistoryStateForTab(tab, mode) {
  return {
    tabId: tab.id,
    view: tab.view,
    query: tab.view === VIEW.SEARCH ? tab.q || "" : "",
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
  buildHistoryStateForTab,
  buildResultSearchHref,
  resolveSearchRestore,
  shouldPushSearchHistory,
  withResultClickQuery,
};