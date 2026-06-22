import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { describe, it } from "node:test";

const root = new URL("../frontend/", import.meta.url);

function readModule(name) {
  return readFileSync(new URL(name, root), "utf8");
}

function assertExports(moduleName, symbols) {
  const source = readModule(moduleName);
  const exportBlocks = source.match(/^export\s*\{/gm) || [];
  assert.ok(
    exportBlocks.length <= 1,
    `${moduleName} must have at most one export block (found ${exportBlocks.length})`,
  );
  for (const symbol of symbols) {
    assert.match(
      source,
      new RegExp(`export\\s*\\{[\\s\\S]*\\b${symbol}\\b`),
      `${moduleName} must export ${symbol}`,
    );
  }
}

describe("frontend ESM public API", () => {
  it("each frontend module has at most one export block", () => {
    for (const name of readdirSync(root).filter((f) => f.endsWith(".mjs"))) {
      const source = readModule(name);
      const blocks = source.match(/^export\s*\{/gm) || [];
      assert.ok(blocks.length <= 1, `${name}: ${blocks.length} export blocks`);
    }
  });

  it("gate.mjs does not assign to imported live bindings", () => {
    const src = readModule("gate.mjs");
    assert.doesNotMatch(src, /import[\s\S]*\blastReadySnapshot\b[\s\S]*from/);
    assert.doesNotMatch(src, /\bappSearchReady\s*=/);
    assert.match(src, /setAppSearchReady\(true\)/);
    assert.match(src, /\nlet lastReadySnapshot\s*=/);
  });

  const MUTABLE_SHELL_KEYS = [
    "tabState",
    "chromeLayout",
    "currentMode",
    "last0243Mode",
    "isSearching",
    "appSearchReady",
    "pendingNewTabAnimation",
  ];

  it("mutable app state is assigned via shell, not imported live bindings", () => {
    assert.match(readModule("app-context.mjs"), /export const shell = \{/);
    for (const name of readdirSync(root).filter((f) => f.endsWith(".mjs") && f !== "app-context.mjs")) {
      const src = readModule(name);
      for (const key of MUTABLE_SHELL_KEYS) {
        assert.doesNotMatch(
          src,
          new RegExp(`(?<!shell\\.)\\b${key}\\s*=`),
          `${name} must not assign to imported ${key}; use shell.${key}`,
        );
      }
    }
  });

  it("gate.mjs exports gate loop entrypoints", () => {
    assertExports("gate.mjs", ["waitForPreloadReady", "wordCacheProgress", "setGateInkProgress"]);
  });

  it("relation-form.mjs exports relation tab API", () => {
    assertExports("relation-form.mjs", [
      "relationPayloadFromForm",
      "applyRelationForm",
      "postRelation",
      "showRelationOk",
      "showRelationErr",
    ]);
  });

  it("tabs-core.mjs exports tab state helpers", () => {
    assertExports("tabs-core.mjs", [
      "activeTab",
      "persistTabs",
      "ensureDefaultTabs",
      "updateBrowserUrlFromActiveTab",
    ]);
  });

  it("tabs-ui.mjs exports tab chrome actions", () => {
    assertExports("tabs-ui.mjs", ["renderTabstrip", "showSearch", "goHome"]);
  });

  it("view-sync.mjs exports syncViewPanels", () => {
    assertExports("view-sync.mjs", ["syncViewPanels"]);
  });

  it("search-workbench.mjs exports search shell API", () => {
    assertExports("search-workbench.mjs", ["searchDict", "toggleMenu", "updateModeLabel"]);
  });

  it("search-navigation.mjs exports result navigation helpers", () => {
    assertExports("search-navigation.mjs", [
      "withResultClickQuery",
      "shouldPushSearchHistory",
      "buildResultSearchHref",
    ]);
  });
});
