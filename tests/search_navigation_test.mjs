import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  createSearchTab,
  VIEW,
  serializeSession,
  deserializeSession,
} from "../frontend/query-tabs-state.mjs";
import {
  withResultClickQuery,
  shouldPushSearchHistory,
  buildResultSearchHref,
  resolveSearchRestore,
  buildHistoryStateForTab,
  ensureSearchTabHistory,
  commitSearchHistoryFrame,
  currentSearchHistoryFrame,
  applyPopstateToSearchTab,
  stepSearchTabBack,
  isHistoryForward,
  shouldApplySearchPopstate,
  resetSearchTabHistory,
} from "../frontend/search-navigation.mjs";

describe("search-navigation", () => {
  it("withResultClickQuery sets tab.q to clicked literal before view sync", () => {
    const tab = createSearchTab({ id: 1, q: "34" });
    const next = withResultClickQuery(tab, "可以");
    assert.equal(next.q, "可以");
    assert.equal(tab.q, "34");
  });

  it("shouldPushSearchHistory replaces when q and mode unchanged", () => {
    const prev = { tabId: 1, view: VIEW.SEARCH, query: "可以", mode: "m1" };
    const next = { tabId: 1, view: VIEW.SEARCH, query: "可以", mode: "m1" };
    assert.equal(shouldPushSearchHistory(next, prev), false);
  });

  it("shouldPushSearchHistory pushes when q changes", () => {
    const prev = { tabId: 1, view: VIEW.SEARCH, query: "34", mode: "m1" };
    const next = { tabId: 1, view: VIEW.SEARCH, query: "可以", mode: "m1" };
    assert.equal(shouldPushSearchHistory(next, prev), true);
  });

  it("buildResultSearchHref encodes q and mode for anchor fallback", () => {
    const href = buildResultSearchHref({
      pathname: "/frontend/index.html",
      query: "可以",
      mode: "m2",
    });
    assert.equal(href, "/frontend/index.html?mode=m2&q=%E5%8F%AF%E4%BB%A5");
  });

  it("resolveSearchRestore prefers cache when key exists", () => {
    const cache = new Map([["m1:可以:0", { data: [{ char: "可以" }], total: 1 }]]);
    const plan = resolveSearchRestore(cache, "m1:可以:0");
    assert.equal(plan.source, "cache");
    assert.deepEqual(plan.entry.data, [{ char: "可以" }]);
  });

  it("resolveSearchRestore fetches when cache misses", () => {
    const plan = resolveSearchRestore(new Map(), "m1:可以:0");
    assert.equal(plan.source, "fetch");
  });

  it("buildHistoryStateForTab captures tabId view query mode", () => {
    const tab = createSearchTab({ id: 3, q: "34" });
    ensureSearchTabHistory(tab, "m1");
    commitSearchHistoryFrame(tab, { q: "34", mode: "m1" });
    assert.deepEqual(buildHistoryStateForTab(tab, "m1"), {
      tabId: 3,
      view: VIEW.SEARCH,
      query: "34",
      mode: "m1",
    });
  });

  it("commitSearchHistoryFrame truncates forward branch after back", () => {
    const tab = createSearchTab({ id: 1, q: "" });
    ensureSearchTabHistory(tab, "m1");
    commitSearchHistoryFrame(tab, { q: "34", mode: "m1" });
    commitSearchHistoryFrame(tab, { q: "可以", mode: "m1" });
    applyPopstateToSearchTab(tab, {
      tabId: 1,
      view: VIEW.SEARCH,
      query: "34",
      mode: "m1",
    });
    commitSearchHistoryFrame(tab, { q: "香港", mode: "m1" });
    assert.deepEqual(tab.historyStack.map((f) => f.q), ["", "34", "香港"]);
    assert.equal(tab.historyIndex, 2);
  });

  it("applyPopstateToSearchTab steps back to blank 新查詢", () => {
    const tab = createSearchTab({ id: 1, q: "可以" });
    ensureSearchTabHistory(tab, "m1");
    commitSearchHistoryFrame(tab, { q: "34", mode: "m1" });
    commitSearchHistoryFrame(tab, { q: "可以", mode: "m1" });
    const frame = applyPopstateToSearchTab(tab, {
      tabId: 1,
      view: VIEW.SEARCH,
      query: "34",
      mode: "m1",
    });
    assert.equal(frame.q, "34");
    assert.equal(tab.historyIndex, 1);
    const home = applyPopstateToSearchTab(tab, {
      tabId: 1,
      view: VIEW.SEARCH,
      query: "",
      mode: "m1",
    });
    assert.equal(home.q, "");
    assert.equal(tab.historyIndex, 0);
  });

  it("stepSearchTabBack steps active tab stack ignoring foreign browser state", () => {
    const tab = createSearchTab({ id: 1, q: "可以" });
    ensureSearchTabHistory(tab, "m1");
    commitSearchHistoryFrame(tab, { q: "34", mode: "m1" });
    commitSearchHistoryFrame(tab, { q: "可以", mode: "m1" });
    const frame = stepSearchTabBack(tab);
    assert.equal(frame.q, "34");
    assert.equal(tab.historyIndex, 1);
    const foreign = applyPopstateToSearchTab(tab, {
      tabId: 2,
      view: VIEW.SEARCH,
      query: "香港",
      mode: "m1",
    });
    assert.equal(foreign.q, "");
    assert.equal(tab.historyIndex, 0);
  });

  it("isHistoryForward detects browser forward navigation", () => {
    assert.equal(isHistoryForward(5, { _histSeq: 7 }), true);
    assert.equal(isHistoryForward(5, { _histSeq: 3 }), false);
    assert.equal(isHistoryForward(5, { _histSeq: 5 }), false);
  });

  it("shouldApplySearchPopstate rejects wrong tab and non-search views", () => {
    const searchTab = createSearchTab({ id: 1, q: "34" });
    const guideTab = { id: 2, view: VIEW.GUIDE, q: "" };
    assert.equal(
      shouldApplySearchPopstate(searchTab, { tabId: 2, view: VIEW.SEARCH, query: "x", mode: "m1" }),
      false
    );
    assert.equal(
      shouldApplySearchPopstate(guideTab, { tabId: 2, view: VIEW.GUIDE, query: "", mode: "m1" }),
      false
    );
    assert.equal(
      shouldApplySearchPopstate(searchTab, { tabId: 1, view: VIEW.SEARCH, query: "34", mode: "m1" }),
      true
    );
  });

  it("serializeSession round-trips per-tab historyStack", () => {
    const tab = createSearchTab({ id: 1, q: "" });
    ensureSearchTabHistory(tab, "m1");
    commitSearchHistoryFrame(tab, { q: "34", mode: "m1" });
    commitSearchHistoryFrame(tab, { q: "可以", mode: "m1" });
    const state = { activeId: 1, nextTabId: 2, tabs: [tab] };
    const restored = deserializeSession(serializeSession(state));
    assert.deepEqual(restored.tabs[0].historyStack.map((f) => f.q), ["", "34", "可以"]);
    assert.equal(restored.tabs[0].historyIndex, 2);
  });

  it("resetSearchTabHistory returns tab to blank root frame", () => {
    const tab = createSearchTab({ id: 1, q: "可以" });
    ensureSearchTabHistory(tab, "m2");
    commitSearchHistoryFrame(tab, { q: "可以", mode: "m2" });
    resetSearchTabHistory(tab, "m2");
    assert.deepEqual(currentSearchHistoryFrame(tab), { q: "", mode: "m2" });
    assert.equal(tab.q, "");
  });
});