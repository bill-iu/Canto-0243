import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { describe, it } from "node:test";

const root = new URL("../shared/", import.meta.url);

function readModule(name) {
  return readFileSync(new URL(name, root), "utf8");
}

function assertExports(moduleName, symbols) {
  const source = readModule(moduleName);
  for (const symbol of symbols) {
    assert.match(
      source,
      new RegExp(`\\bexport\\b[\\s\\S]*\\b${symbol}\\b`),
      `${moduleName} must export ${symbol}`,
    );
  }
}

/** #86 stage (2): Portable shell entry modules removed; shared + chrome-tabs remain. */
const REMOVED_SHELL_MODULES = [
  "main.mjs",
  "gate.mjs",
  "search-workbench.mjs",
  "tabs-core.mjs",
  "tabs-ui.mjs",
  "view-sync.mjs",
  "relation-form.mjs",
  "lexicon-corrections.mjs",
  "entry-detail-portable.mjs",
  "query-explain.mjs",
  "mode-policy.mjs",
  "ping-ze-syntax.mjs",
  "dom-escape.mjs",
];

describe("frontend ESM public API", () => {
  it("Portable shell-only modules are gone", () => {
    const names = new Set(readdirSync(root).filter((f) => f.endsWith(".mjs")));
    for (const name of REMOVED_SHELL_MODULES) {
      assert.ok(!names.has(name), `expected removed: ${name}`);
    }
  });

  it("mutable app state is assigned via shell, not imported live bindings", () => {
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

  it("search-navigation.mjs exports result navigation helpers", () => {
    assertExports("search-navigation.mjs", [
      "withResultClickQuery",
      "commitSearchHistoryFrame",
      "shouldApplySearchPopstate",
      "buildResultSearchHref",
    ]);
  });

  it("chrome-tabs-layout.mjs exports QueryChromeTabsLayout", () => {
    assert.match(readModule("chrome-tabs-layout.mjs"), /export class QueryChromeTabsLayout/);
  });
});

describe("ready-gate dual-channel assets", () => {
  it("pwa ready-gate brand defs contain icon and ink symbols", () => {
    const defsSrc = readFileSync(new URL("../client/src/brand-svg-defs.tsx", import.meta.url), "utf8");
    assert.match(defsSrc, /id="brand-wordmark"/);
    assert.match(defsSrc, /id="brand-ink-blob"/);
    assert.match(defsSrc, /id="brand-ink-flicks"/);
  });

  it("pwa brand-logo gate variant contains icon and ink uses", () => {
    const logoSrc = readFileSync(new URL("../client/src/brand-logo.tsx", import.meta.url), "utf8");
    assert.match(logoSrc, /#brand-wordmark/);
    assert.match(logoSrc, /#brand-ink-blob/);
    assert.match(logoSrc, /#brand-ink-flicks/);
    assert.match(logoSrc, /href=\{wordmark\}/);
    assert.match(logoSrc, /className="gate-ink-track"/);
    assert.match(logoSrc, /className="gate-ink-fill"/);
  });

  it("ready-gate always renders gate-brand when visible", () => {
    const gateSrc = readFileSync(new URL("../client/src/ready-gate.tsx", import.meta.url), "utf8");
    assert.match(gateSrc, /<div className="gate-brand">/);
    assert.match(gateSrc, /<BrandLogo variant="gate"/);
  });

  it("ready-gate narrow uses upward optical offset and full-viewport flex center", () => {
    const css = readFileSync(new URL("../shared/ready-gate.css", import.meta.url), "utf8");
    assert.match(css, /padding-top: 0/);
    assert.match(css, /justify-content: center/);
    assert.match(css, /@media \(max-width: 760px\)[\s\S]*translateY\(calc\(-4vh/);
  });

  it("shell-revealed is channel-neutral for gate unlock (Portable + PWA)", () => {
    const css = readFileSync(new URL("../shared/ready-gate.css", import.meta.url), "utf8");
    assert.match(css, /html:not\(\.shell-revealed\) \.app-shell/);
    assert.ok(!css.includes("pwa-shell-revealed"));
    const boot = readFileSync(new URL("../client/src/pwa-shell-boot.ts", import.meta.url), "utf8");
    assert.match(boot, /shell-revealed/);
    assert.ok(!boot.includes("pwa-shell-revealed"));
    const portableReady = readFileSync(
      new URL("../client/src/hooks/use-portable-ready.ts", import.meta.url),
      "utf8",
    );
    assert.match(portableReady, /fetch\('\/ready'/);
    assert.match(portableReady, /gate_ready/);
  });

  it("lexicon open defaults to opfs-vfs with sqljs degrade hooks", () => {
    const modeSrc = readFileSync(new URL("../client/src/db/db-backend-mode.ts", import.meta.url), "utf8");
    assert.match(modeSrc, /if \(raw === 'sqljs'\) return 'sqljs'/);
    assert.match(modeSrc, /return 'opfs-vfs'/);
    const initSrc = readFileSync(new URL("../client/src/db/init.ts", import.meta.url), "utf8");
    assert.match(initSrc, /openLexiconDatabase/);
    assert.match(initSrc, /markOpfsVfsSessionSkip/);
    assert.match(initSrc, /getActiveDbBackendMode/);
    const appSrc = readFileSync(new URL("../client/src/App.tsx", import.meta.url), "utf8");
    assert.match(appSrc, /getActiveDbBackendMode\(\) === 'opfs-vfs'/);
  });
});
