/** Realms, immutable build assets, persistence, and retry must agree before readiness. */
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build as bundle } from 'esbuild';
import { build as viteBuild } from 'vite';
import { generateSW } from 'workbox-build';
import configFactory, { pwaPrecachePatterns, pwaRuntimeCaching, rankingIndexAssetPlugin, rankingIndexBuildAsset } from '../vite.config.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = {
  essay: { 一級: 1, 高頻: 100 }, curated: [], pronRank: {},
  wordUsage: { 一級: [1, 0], 高頻: [1, 0] },
};
const text = JSON.stringify(data);
const asset = rankingIndexBuildAsset(new TextEncoder().encode(text));
const expectedUrl = `/Canto-0243/${asset.fileName}`;
const rows = [{ char: '一級' }, { char: '高頻' }];
let realmNumber = 0;

async function realm(fingerprint = asset.sha256, dev = false) {
  const result = await bundle({
    stdin: {
      contents: `export * from ${JSON.stringify(path.join(root, 'src/db/ranking-index-browser.ts'))};
export {initRankingData,sortWordRows} from ${JSON.stringify(path.join(root, 'src/db/ranking.ts'))};`,
      resolveDir: root, loader: 'ts',
    },
    bundle: true, write: false, format: 'esm', platform: 'browser',
    define: { 'import.meta.env': JSON.stringify({ BASE_URL: '/Canto-0243/', DEV: dev, VITE_RANKING_INDEX_SHA256: fingerprint }) },
  });
  const code = result.outputFiles[0]!.text + `\n// realm ${realmNumber++}`;
  return import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
}

const stored = new Map<string, Response>();
let failPut = false;
const cache = {
  async match(key: string) { return stored.get(key)?.clone(); },
  async put(key: string, response: Response) {
    if (failPut) throw new Error('quota failure');
    stored.set(key, response.clone());
  },
  async delete(key: string) { return stored.delete(key); },
};
const originalCaches = Object.getOwnPropertyDescriptor(globalThis, 'caches');
const originalFetch = globalThis.fetch;
const originalWarn = console.warn;
const setCaches = (value: unknown) => Object.defineProperty(globalThis, 'caches', { configurable: true, value });
const fixture = await mkdtemp(path.join(os.tmpdir(), 'canto-ranking-'));
assert.equal(path.dirname(path.resolve(fixture)), path.resolve(os.tmpdir()));

try {
  setCaches({ open: async () => cache });
  const main = await realm();
  const failures: Array<() => Promise<Response>> = [
    async () => { throw new TypeError('Network request failed'); },
    async () => new Response('', { status: 503 }),
    async () => new Response('<html>offline</html>'),
    async () => Response.json({}),
    async () => Response.json({ ...data, essay: {} }),
    async () => Response.json({ ...data, wordUsage: undefined }),
    async () => Response.json({ ...data, wordUsage: {} }),
    async () => Response.json({ ...data, wordUsage: [] }),
    async () => Response.json({ ...data, wordUsage: { 一級: [99, -1] } }),
    async () => Response.json({ ...data, wordUsage: { 一級: [0, 0], 高頻: [2, 0] } }),
  ];
  for (const fail of failures) {
    stored.clear();
    main.resetBrowserRankingIndex();
    main.initRankingData({ essay: {}, curated: [], pronRank: {}, wordUsage: {} });
    let calls = 0;
    globalThis.fetch = async input => {
      assert.equal(input, expectedUrl);
      calls += 1;
      return calls === 1 ? fail() : new Response(text);
    };
    await assert.rejects(main.loadBrowserRankingIndex(), 'failed ranking must not complete readiness');
    assert.equal(stored.size, 0, 'invalid bytes must not enter the persistent cache');
    await main.loadBrowserRankingIndex();
    assert.equal(calls, 2, 'failed initialization remains retryable');
    assert.deepEqual(main.sortWordRows(rows).map((row: { char: string }) => row.char), ['高頻', '一級']);
    await main.loadBrowserRankingIndex();
    assert.equal(calls, 2, 'successful initialization is reused within its realm');
  }

  globalThis.fetch = async () => { throw new Error('offline'); };
  const worker = await realm();
  await worker.loadBrowserRankingIndex();
  assert.deepEqual(worker.sortWordRows(rows).map((row: { char: string }) => row.char), ['高頻', '一級'],
    'a fresh worker realm must initialize from the persisted index while offline');
  main.resetBrowserRankingIndex();
  await main.loadBrowserRankingIndex();

  // Same v1.1.2 tag, changed ranking data: different content URL, no stale table.
  const nextText = JSON.stringify({ ...data, wordUsage: { 一級: [0, 0], 高頻: [2, 0] } });
  const nextAsset = rankingIndexBuildAsset(new TextEncoder().encode(nextText));
  assert.notEqual(nextAsset.fileName, asset.fileName);
  const next = await realm(nextAsset.sha256);
  let nextCalls = 0;
  globalThis.fetch = async input => {
    assert.equal(input, `/Canto-0243/${nextAsset.fileName}`);
    nextCalls += 1;
    return new Response(nextText);
  };
  await next.loadBrowserRankingIndex();
  assert.equal(nextCalls, 1);
  assert.deepEqual(next.sortWordRows(rows).map((row: { char: string }) => row.char), ['一級', '高頻'],
    'reviewed word usage must outrank Essay frequency');
  assert.deepEqual(worker.sortWordRows(rows).map((row: { char: string }) => row.char), ['高頻', '一級'],
    'realm-local state is independent');
  globalThis.fetch = async () => { throw new Error('offline'); };
  const nextWorker = await realm(nextAsset.sha256);
  await nextWorker.loadBrowserRankingIndex();
  assert.deepEqual(nextWorker.sortWordRows(rows).map((row: { char: string }) => row.char), ['一級', '高頻']);

  stored.clear();
  stored.set(expectedUrl, new Response(nextText));
  const corrupted = await realm();
  await assert.rejects(corrupted.loadBrowserRankingIndex(), /identity mismatch/);
  assert.equal(stored.has(expectedUrl), false, 'a corrupt cache entry is removed before retry');
  globalThis.fetch = async () => new Response(text);
  await corrupted.loadBrowserRankingIndex();

  stored.clear();
  const blockedStorage = await realm();
  failPut = true;
  await assert.rejects(blockedStorage.loadBrowserRankingIndex(), /quota failure/);
  failPut = false;
  await blockedStorage.loadBrowserRankingIndex();
  const missingIdentity = await realm('');
  await assert.rejects(missingIdentity.loadBrowserRankingIndex(), /Missing ranking index identity/);

  const dev = await realm('', true);
  setCaches(undefined);
  console.warn = () => undefined;
  globalThis.fetch = async () => new Response('', { status: 404 });
  await dev.loadBrowserRankingIndex();
  globalThis.fetch = async input => {
    assert.equal(input, '/Canto-0243/ranking-index.json');
    return new Response(text);
  };
  await dev.loadBrowserRankingIndex();
  assert.deepEqual(dev.sortWordRows(rows).map((row: { char: string }) => row.char), ['高頻', '一級']);

  assert.equal(typeof configFactory, 'function');
  if (typeof configFactory !== 'function') throw new Error('Expected Vite config factory');
  const portable = await configFactory({ command: 'build', mode: 'portable' });
  assert.equal(portable.define?.['import.meta.env.VITE_RANKING_INDEX_SHA256'], '""');
  assert(!portable.plugins?.flat().some(plugin => plugin && 'name' in plugin && plugin.name === 'ranking-index-identity'),
    'Desktop must not require or emit PWA ranking assets that escape its strip policy');

  // Real Vite output must bind both window and worker to the emitted content asset.
  const loader = path.join(root, 'src/db/ranking-index-browser.ts').replaceAll('\\', '/');
  await writeFile(path.join(fixture, 'index.html'), '<script type="module" src="/main.ts"></script>');
  await writeFile(path.join(fixture, 'main.ts'), `import {loadBrowserRankingIndex} from ${JSON.stringify(loader)};
new Worker(new URL('./worker.ts', import.meta.url), {type:'module'}); void loadBrowserRankingIndex();`);
  await writeFile(path.join(fixture, 'worker.ts'), `import {loadBrowserRankingIndex} from ${JSON.stringify(loader)}; void loadBrowserRankingIndex();`);
  const built = await viteBuild({
    configFile: false, root: fixture, base: '/Canto-0243/', logLevel: 'silent',
    plugins: [rankingIndexAssetPlugin(asset)],
    define: { 'import.meta.env.VITE_RANKING_INDEX_SHA256': JSON.stringify(asset.sha256) },
    build: { write: false, minify: false },
  });
  const outputs = (Array.isArray(built) ? built : [built]).flatMap(result => 'output' in result ? result.output : []);
  const emitted = outputs.find(output => output.fileName === asset.fileName);
  assert(emitted && emitted.type === 'asset');
  assert.equal(Buffer.from(emitted.source).toString(), text);
  const js = outputs.filter(output => output.fileName.endsWith('.js'));
  assert(js.length >= 2, 'window and worker are both bundled');
  for (const output of js) {
    const code = output.type === 'chunk' ? output.code : Buffer.from(output.source).toString();
    assert(code.includes(asset.sha256), `ranking identity missing from ${output.fileName}`);
  }

  await generateSW({
    globDirectory: fixture, swDest: path.join(fixture, 'sw.js'),
    globPatterns: pwaPrecachePatterns, runtimeCaching: pwaRuntimeCaching,
    inlineWorkboxRuntime: true, mode: 'development',
  });
  const sw = await readFile(path.join(fixture, 'sw.js'), 'utf8');
  assert(sw.includes('lexicon-manifest-cache') && sw.includes('database-cache'));
  assert(!sw.includes('ranking-index-cache') && !sw.includes('StaleWhileRevalidate'));
} finally {
  globalThis.fetch = originalFetch;
  console.warn = originalWarn;
  if (originalCaches) Object.defineProperty(globalThis, 'caches', originalCaches);
  else Reflect.deleteProperty(globalThis, 'caches');
  await rm(fixture, { recursive: true, force: true });
}

console.log('ranking-index-browser-self-check: ok (identity, schema, retry, persistence, offline realms, same-tag refresh, Vite worker, Workbox)');
