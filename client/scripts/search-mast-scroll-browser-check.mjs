/** Real layout regression: node scripts/search-mast-scroll-browser-check.mjs
 * Requires Playwright + Chromium (an external install can be supplied via NODE_PATH).
 * No lexicon or running app server is needed. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const { chromium } = createRequire(import.meta.url)('playwright');
const root = fileURLToPath(new URL('..', import.meta.url));
const shared = fileURLToPath(new URL('../../shared', import.meta.url)).replaceAll('\\', '/');
const server = await createServer({
  root,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, fs: { allow: [fileURLToPath(new URL('../..', import.meta.url))] } },
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Use the production CSS and controller, without database/React startup.
  await page.route('**/mast-scroll-check', route => route.fulfill({
    contentType: 'text/html',
    body: `<!doctype html><html class="shell-revealed"><head>
      <link rel="stylesheet" href="/@fs/${shared}/open-design.css">
      <link rel="stylesheet" href="/@fs/${shared}/shell.css">
      <link rel="stylesheet" href="/@fs/${shared}/entry-detail.css">
      <link rel="stylesheet" href="/src/root.css">
      <link rel="stylesheet" href="/src/pwa-app.css">
      </head><body class="query-tabs-app">
      <div class="app-shell"><header class="app-header">
        <div class="query-tabs-bar"><button class="query-tab-pill">43有</button><button class="query-tab-add">+</button></div>
        <div class="app-bar">
          <div class="header-mast"><div class="header-mast__track">
            <button class="brand"><svg class="brand-logo" width="200" height="72" viewBox="0 0 200 72"></svg></button>
            <div class="header-hero"><p class="header-hero__title">ONE·搵·韻</p><p class="header-hero__tagline">格律／協音／押韻／近反義，一步搵到。</p></div>
          </div></div>
          <div class="header-chrome__actions"><div class="app-actions mode-menu-root">
            <div class="mode-menu-stack"><div class="mode-menu-anchor"><button class="menu-trigger">0243模式</button></div></div>
            <p class="mode-menu-meta">詞庫版本：v1.1.1 · OPFS</p>
          </div></div>
          <div class="header-search"><div class="header-search__row"><input value="43有"></div><div class="header-search__meta">正韻</div></div>
        </div>
      </header><main class="main-wrap"><section class="search-view"><div class="search-view__main"><div class="search-results"><div class="search-results-scroll"><div id="content"></div></div></div></div></section></main></div>
      <script type="module">
        import { bindSearchMastScroll } from '/src/search-mast-scroll.ts';
        window.unbind = bindSearchMastScroll(document.querySelector('.app-bar'), document.querySelector('.app-shell'));
      </script></body></html>`,
  }));
  const url = `http://127.0.0.1:${server.httpServer.address().port}/mast-scroll-check`;
  for (const { width, overflow, reducedMotion, scroller = 'results' } of [
    { width: 1920, overflow: 20 },
    { width: 1920, overflow: 60 },
    { width: 1024, overflow: 60 },
    { width: 761, overflow: 60 },
    { width: 1920, overflow: 60, reducedMotion: 'reduce' },
    { width: 1920, overflow: 600 },
    { width: 1920, overflow: 0 },
    { width: 1920, overflow: 60, scroller: 'columns' },
    { width: 900, overflow: 60, scroller: 'rows' },
    { width: 390, overflow: 600 },
  ]) {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: reducedMotion ?? 'no-preference' });
    await page.goto(url);
    await page.waitForFunction(() => typeof window.unbind === 'function');
    const result = await page.evaluate(async ({ overflow, scroller }) => {
      const shell = document.querySelector('.app-shell');
      const appBar = shell.querySelector('.app-bar');
      const header = shell.querySelector('.app-header');
      let root = shell.querySelector('.search-results-scroll');
      if (scroller !== 'results') {
        shell.querySelector('.search-view').classList.add('is-empty-landing');
        root.innerHTML = `<div class="guide-quick"><div class="guide-quick__${scroller}" style="display:block"><div id="content"></div></div></div>`;
        root = root.querySelector(`.guide-quick__${scroller}`);
      }
      const frame = () => new Promise(requestAnimationFrame);
      await frame();
      const expanded = header.getBoundingClientRect().height;
      const meta = shell.querySelector('.mode-menu-meta');
      const metaTop = meta.getBoundingClientRect().top;
      shell.querySelector('#content').style.height = `${root.clientHeight + overflow - parseFloat(getComputedStyle(root).paddingBottom)}px`;
      const target = Math.min(overflow, overflow > 100 ? 160 : 40);
      root.scrollTop = target;
      const samples = [];
      for (let i = 0; i < 30; i++) {
        await frame();
        samples.push({ top: root.scrollTop, height: header.getBoundingClientRect().height });
      }
      const y = parseFloat(appBar.style.getPropertyValue('--mast-y'));
      const collapsed = appBar.classList.contains('is-mast-collapsed');
      const metaShift = metaTop - meta.getBoundingClientRect().top;
      const metaHidden = getComputedStyle(meta).display === 'none';
      const metaClip = parseFloat(getComputedStyle(meta).clipPath.slice('inset('.length)) || 0;
      const metaBox = meta.getBoundingClientRect();
      const metaOverlapsMenu = metaClip < metaBox.height
        && metaBox.top + metaClip < shell.querySelector('.menu-trigger').getBoundingClientRect().bottom - 0.5;
      root.scrollTop = 0;
      await frame();
      await frame();
      const restored = header.getBoundingClientRect().height;
      const restoredMetaTop = meta.getBoundingClientRect().top;
      window.unbind();
      return { samples, target, y, collapsed, expanded, restored, metaTop, metaShift, metaHidden, metaOverlapsMenu, restoredMetaTop, cleanup: shell.style.getPropertyValue('--mast-scroll-space') };
    }, { overflow, scroller });
    const label = `${width}px ${scroller} overflow=${overflow} ${reducedMotion ?? ''}`;
    for (const sample of result.samples.slice(-10)) {
      assert.ok(Math.abs(sample.top - result.target) < 1, `${label}: scroll position clamped`);
      assert.ok(Math.abs(sample.height - result.samples.at(-1).height) < 1, `${label}: header oscillates`);
    }
    assert.ok(Math.abs(result.restored - result.expanded) < 1, `${label}: header must expand at top`);
    assert.equal(result.cleanup, '', `${label}: cleanup`);
    if (width >= 761) {
      assert.ok(Math.abs(result.metaTop - result.restoredMetaTop) < 1, `${label}: lexicon meta returns at top`);
      assert.ok(!result.metaOverlapsMenu, `${label}: lexicon meta cannot overlap menu`);
      if (result.collapsed) assert.ok(result.metaHidden, `${label}: lexicon meta hides with mast`);
      else assert.ok(Math.abs(result.metaShift - result.y) < 1, `${label}: lexicon meta must track mast 1:1 (moved ${result.metaShift}px for ${result.y}px)`);
    }
    if (overflow === 60 && !reducedMotion) assert.equal(result.y, 40, `${label}: partial collapse`);
    if (overflow > 100 || reducedMotion) assert.ok(result.collapsed, `${label}: full collapse`);
    if (!overflow) assert.equal(result.y, 0, `${label}: fitting content stays expanded`);
    console.log(`PASS ${label}`);
  }
  assert.deepEqual(errors, []);
} finally {
  await browser?.close();
  await server.close();
}
