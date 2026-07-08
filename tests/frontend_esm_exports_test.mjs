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
    "lastHistSeq",
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
      "commitSearchHistoryFrame",
      "shouldApplySearchPopstate",
      "buildResultSearchHref",
    ]);
  });

  it("query-explain.mjs exports live explain API", () => {
    assertExports("query-explain.mjs", [
      "refreshQueryExplain",
      "scheduleQueryExplain",
      "clearQueryExplain",
    ]);
  });
});

describe("PWA ready-gate assets", () => {
  // PWA 就緒閘 icon (brand-wordmark) 和 ink (brand-ink-*) 防止消失的 source 檢查
  // 未來改動若移除 <use> 或 <symbol> 會 fail，保護動畫元素
  it("pwa ready-gate brand defs contain icon and ink symbols", () => {
    const defsSrc = readFileSync(new URL("../client/src/brand-svg-defs.tsx", import.meta.url), "utf8");
    assert.match(defsSrc, /id="brand-wordmark"/);
    assert.match(defsSrc, /id="brand-ink-blob"/);
    assert.match(defsSrc, /id="brand-ink-flicks"/);
  });

  it("pwa brand-logo gate variant contains icon and ink uses", () => {
    const logoSrc = readFileSync(new URL("../client/src/brand-logo.tsx", import.meta.url), "utf8");
    assert.match(logoSrc, /href="#brand-wordmark"/);
    assert.match(logoSrc, /href="#brand-ink-blob"/);
    assert.match(logoSrc, /href="#brand-ink-flicks"/);
    assert.match(logoSrc, /className="gate-ink-track"/);
    assert.match(logoSrc, /className="gate-ink-fill"/);
  });

  it("ready-gate always renders gate-brand icon and gate-ink-meter (logo+ink) when visible", () => {
    const gateSrc = readFileSync(new URL("../client/src/ready-gate.tsx", import.meta.url), "utf8");
    // Ensures no conditional that could hide the logo/ink elements in the animation
    assert.match(gateSrc, /<div className="gate-brand">/);
    assert.match(gateSrc, /<BrandLogo variant="gate"/);
    assert.match(gateSrc, /<GateInkMeter/);
  });

  it("ready-gate shows overlay during warm lexicon open from local cache", () => {
    const gateSrc = readFileSync(new URL("../client/src/ready-gate.tsx", import.meta.url), "utf8");
    assert.match(gateSrc, /offlineStatus === 'preparing' && Boolean\(isDbCached\)/);
    const appSrc = readFileSync(new URL("../client/src/App.tsx", import.meta.url), "utf8");
    assert.match(appSrc, /isDbCached !== true/);
  });

  it("lexicon open defaults to opfs-vfs with sqljs degrade hooks", () => {
    const modeSrc = readFileSync(new URL("../client/src/db/db-backend-mode.ts", import.meta.url), "utf8");
    assert.match(modeSrc, /if \(raw === 'sqljs'\) return 'sqljs'/);
    assert.match(modeSrc, /return 'opfs-vfs'/);
    const initSrc = readFileSync(new URL("../client/src/db/init.ts", import.meta.url), "utf8");
    assert.match(initSrc, /openLexiconDatabase/);
    assert.match(initSrc, /markOpfsVfsSessionSkip/);
    assert.match(initSrc, /getActiveDbBackendMode/);
    const engineSrc = readFileSync(new URL("../client/src/db/position-match/engine.ts", import.meta.url), "utf8");
    assert.match(engineSrc, /hybrid_ref_chars[\s\S]*unlimited:\s*true/);
    const appSrc = readFileSync(new URL("../client/src/App.tsx", import.meta.url), "utf8");
    assert.match(appSrc, /getActiveDbBackendMode\(\) === 'opfs-vfs'/);
  });

  it("shell.css has rules to show gate-brand in non-minimal mode", () => {
    const shellSrc = readFileSync(new URL("../frontend/shell.css", import.meta.url), "utf8");
    assert.match(shellSrc, /:not\(.minimal.\) .gate-brand/);
    assert.match(shellSrc, /html\.fonts-ready .gate-brand/);
  });
});
