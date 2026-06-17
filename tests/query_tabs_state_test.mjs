import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  SESSION_KEY,
  TAB_LABEL_MAX,
  VIEW,
  tabLabel,
  findTabByView,
  openSingletonView,
  createSearchTab,
  createGuideTab,
  createRelationTab,
  buildUrlSearchParams,
  parseUrlSearchParams,
  searchParamsWithoutBoot,
  LAUNCHER_BOOT_PARAM,
  serializeSession,
  deserializeSession,
  closeTab,
  reorderTab,
  reorderTabsByIds,
  applyUrlToTabs,
} from "../frontend/query-tabs-state.mjs";

describe("query-tabs-state", () => {
  it("exports production session key", () => {
    assert.equal(SESSION_KEY, "canto0243:query-tabs");
  });

  it("labels search tabs by query or 新查詢", () => {
    assert.equal(tabLabel({ view: VIEW.SEARCH, q: "" }), "新查詢");
    assert.equal(tabLabel({ view: VIEW.SEARCH, q: "香??" }), "香??");
    const long = "x".repeat(TAB_LABEL_MAX + 5);
    assert.equal(tabLabel({ view: VIEW.SEARCH, q: long }), `${"x".repeat(TAB_LABEL_MAX)}…`);
  });

  it("labels guide and relation tabs with fixed copy", () => {
    assert.equal(tabLabel({ view: VIEW.GUIDE }), "搜尋教學");
    assert.equal(tabLabel({ view: VIEW.RELATION }), "補關係");
  });

  it("openSingletonView switches to existing guide tab instead of duplicating", () => {
    let state = {
      activeId: 1,
      nextTabId: 2,
      tabs: [createSearchTab({ id: 1, q: "~~" })],
    };
    const first = openSingletonView(state, VIEW.GUIDE, createGuideTab);
    assert.equal(first.tabs.length, 2);
    assert.equal(first.tabs[1].view, VIEW.GUIDE);
    assert.equal(first.activeId, first.tabs[1].id);

    const second = openSingletonView(first, VIEW.GUIDE, createGuideTab);
    assert.equal(second.tabs.length, 2);
    assert.equal(second.activeId, first.tabs[1].id);
  });

  it("openSingletonView switches to existing relation tab instead of duplicating", () => {
    let state = {
      activeId: 1,
      nextTabId: 2,
      tabs: [createSearchTab({ id: 1, q: "" })],
    };
    const first = openSingletonView(state, VIEW.RELATION, createRelationTab);
    const relationId = first.tabs[1].id;
    const second = openSingletonView(first, VIEW.RELATION, createRelationTab);
    assert.equal(second.tabs.length, 2);
    assert.equal(second.activeId, relationId);
  });

  it("buildUrlSearchParams reflects active tab view in URL", () => {
    const search = buildUrlSearchParams({ view: VIEW.SEARCH, q: "香??" }, "m1");
    assert.equal(search.get("q"), "香??");
    assert.equal(search.get("view"), null);

    const guide = buildUrlSearchParams({ view: VIEW.GUIDE }, "m2");
    assert.equal(guide.get("view"), "guide");
    assert.equal(guide.get("mode"), "m2");
    assert.equal(guide.get("q"), null);

    const relation = buildUrlSearchParams({ view: VIEW.RELATION }, "m1");
    assert.equal(relation.get("view"), "relation");
    assert.equal(relation.get("q"), null);
  });

  it("parseUrlSearchParams normalizes view and mode", () => {
    const params = new URLSearchParams("view=relation&mode=m3&q=ignored");
    const parsed = parseUrlSearchParams(params);
    assert.equal(parsed.view, VIEW.RELATION);
    assert.equal(parsed.mode, "m3");
    assert.equal(parsed.q, "ignored");
  });

  it("searchParamsWithoutBoot drops launcher cache-bust only", () => {
    const withBoot = new URLSearchParams("boot=1781737611&q=香");
    const stripped = searchParamsWithoutBoot(withBoot);
    assert.equal(stripped?.get("boot"), null);
    assert.equal(stripped?.get("q"), "香");

    const bare = new URLSearchParams("q=香");
    assert.equal(searchParamsWithoutBoot(bare), null);
  });

  it("serializeSession round-trips tabs including relation draft", () => {
    const state = {
      activeId: 2,
      nextTabId: 3,
      tabs: [
        createSearchTab({ id: 1, q: "~~", results: ["朋友"], offset: 0, total: 1 }),
        createRelationTab({
          id: 2,
          relation: { seed_char: "快樂", opposite_char: "開心", relation_type: "syn" },
        }),
      ],
    };
    const raw = serializeSession(state);
    const payload = JSON.parse(raw);
    assert.equal(payload.tabs[0].results, undefined);
    const restored = deserializeSession(raw);
    assert.deepEqual(restored.tabs[0].results, []);
    assert.deepEqual(restored.tabs[1].relation, state.tabs[1].relation);
    assert.equal(restored.activeId, 2);
    assert.equal(restored.nextTabId, 3);
  });

  it("closeTab refuses to remove the last tab", () => {
    const state = {
      activeId: 1,
      nextTabId: 2,
      tabs: [createSearchTab({ id: 1, q: "" })],
    };
    const next = closeTab(state, 1);
    assert.equal(next.tabs.length, 1);
  });

  it("applyUrlToTabs opens singleton guide tab from view=guide when session empty", () => {
    const parsed = parseUrlSearchParams(new URLSearchParams("view=guide&mode=m1"));
    const state = applyUrlToTabs(null, parsed);
    assert.equal(state.tabs.length, 1);
    assert.equal(state.tabs[0].view, VIEW.GUIDE);
    assert.equal(state.activeId, state.tabs[0].id);
  });

  it("reorderTab moves a tab within the tabs array", () => {
    const state = {
      activeId: 1,
      nextTabId: 4,
      tabs: [
        createSearchTab({ id: 1, q: "a" }),
        createSearchTab({ id: 2, q: "b" }),
        createGuideTab({ id: 3 }),
      ],
    };
    const next = reorderTab(state, 0, 2);
    assert.deepEqual(
      next.tabs.map((t) => t.id),
      [2, 3, 1]
    );
    assert.equal(next.activeId, 1);
  });

  it("reorderTab no-ops on invalid or unchanged indices", () => {
    const state = {
      activeId: 1,
      nextTabId: 2,
      tabs: [createSearchTab({ id: 1, q: "" })],
    };
    assert.equal(reorderTab(state, 0, 0), state);
    assert.equal(reorderTab(state, -1, 0), state);
    assert.equal(reorderTab(state, 0, 3), state);
  });

  it("reorderTabsByIds reorders tabs to match the given id list", () => {
    const state = {
      activeId: 2,
      nextTabId: 4,
      tabs: [
        createSearchTab({ id: 1, q: "a" }),
        createSearchTab({ id: 2, q: "b" }),
        createRelationTab({ id: 3 }),
      ],
    };
    const next = reorderTabsByIds(state, [3, 1, 2]);
    assert.deepEqual(
      next.tabs.map((t) => t.id),
      [3, 1, 2]
    );
    assert.equal(next.activeId, 2);
  });

  it("serializeSession preserves tab order after reorder", () => {
    const state = reorderTab(
      {
        activeId: 1,
        nextTabId: 3,
        tabs: [createSearchTab({ id: 1, q: "a" }), createGuideTab({ id: 2 })],
      },
      0,
      1
    );
    const restored = deserializeSession(serializeSession(state));
    assert.deepEqual(
      restored.tabs.map((t) => t.id),
      [2, 1]
    );
  });
});
