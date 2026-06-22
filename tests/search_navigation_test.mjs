import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createSearchTab, VIEW } from "../frontend/query-tabs-state.mjs";
import {
  withResultClickQuery,
  shouldPushSearchHistory,
  buildResultSearchHref,
  resolveSearchRestore,
  buildHistoryStateForTab,
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
    assert.deepEqual(buildHistoryStateForTab(tab, "m1"), {
      tabId: 3,
      view: VIEW.SEARCH,
      query: "34",
      mode: "m1",
    });
  });
});