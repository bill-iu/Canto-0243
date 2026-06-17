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

  it("gate.mjs exports gate loop entrypoints", () => {
    assertExports("gate.mjs", ["waitForPreloadReady", "wordCacheProgress", "setGateInkProgress"]);
    assert.doesNotMatch(readModule("gate.mjs"), /\nlet lastReadySnapshot\s*=/);
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
});
