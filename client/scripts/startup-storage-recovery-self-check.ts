/** Real storage/Worker code, with deterministic browser faults and interleavings. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { webcrypto } from 'node:crypto';
import { build } from 'esbuild';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const defer = () => { let resolve!: (v?: any) => void; const promise = new Promise<any>(r => { resolve = r; }); return { promise, resolve }; };
const env = { BASE_URL: '/Canto-0243/', VITE_DB_BACKEND: 'opfs-vfs', DEV: true };
async function compile(file: string, extra = '', stubs: Record<string, string> = {}) {
  const result = await build({
    stdin: { contents: (await readFile(path.join(root, file), 'utf8')) + extra, resolveDir: path.dirname(path.join(root, file)), loader: 'ts' },
    bundle: true, write: false, format: 'iife', globalName: 'subject', platform: 'browser',
    logOverride: { 'empty-import-meta': 'silent' },
    define: { 'import.meta.env': JSON.stringify(env), 'import.meta.url': JSON.stringify('https://test.invalid/assets/module.js') },
    plugins: [{ name: 'fault-boundaries', setup(b) {
      b.onResolve({ filter: /.*/ }, args => {
        const key = Object.keys(stubs).find(key => args.path.endsWith(key));
        return key ? { path: key, namespace: 'fault' } : undefined;
      });
      b.onLoad({ filter: /.*/, namespace: 'fault' }, args => ({ contents: stubs[args.path], loader: 'ts' }));
    } }],
  });
  return result.outputFiles[0]!.text;
}
function realm(code: string, values: Record<string, unknown> = {}) {
  const sandbox = vm.createContext({ console, URL, DOMException, Uint8Array, ArrayBuffer, TextEncoder,
    TextDecoder, Response, ReadableStream, crypto: webcrypto, performance, setTimeout, clearTimeout,
    navigator: {}, self: { postMessage() {} }, ...values });
  vm.runInContext(code, sandbox);
  return sandbox;
}
function disk(asyncWriter = false) {
  const files = new Map<string, Uint8Array>();
  const locked = new Set<string>();
  let failure: string | null = null;
  let partial = 65536;
  let closes = 0;
  let flushes = 0;
  const check = () => { if (failure) throw new DOMException('Injected storage failure', failure); };
  const rootDir = {
    async getFileHandle(name: string, options?: { create?: boolean }) {
      check();
      if (!files.has(name)) {
        if (!options?.create) throw new DOMException('Missing', 'NotFoundError');
        files.set(name, new Uint8Array());
      }
      return {
        async getFile() { check(); const bytes = files.get(name)!; return { size: bytes.length, arrayBuffer: async () => bytes.slice().buffer }; },
        ...(asyncWriter ? { async createWritable() {
          check(); let bytes = new Uint8Array();
          return { async write(chunk: Uint8Array) { check(); const next = new Uint8Array(bytes.length + chunk.length); next.set(bytes); next.set(chunk, bytes.length); bytes = next; },
            async truncate(n: number) { bytes = bytes.slice(0, n); }, async close() { files.set(name, bytes); closes++; }, async abort() { closes++; } };
        } } : {}),
        async createSyncAccessHandle() {
          check();
          if (locked.has(name)) throw new DOMException('Busy', 'NoModificationAllowedError');
          locked.add(name);
          return {
            write(bytes: Uint8Array, { at }: { at: number }) { check(); const size = Math.min(partial, bytes.length); const old = files.get(name)!; const next = new Uint8Array(Math.max(old.length, at + size)); next.set(old); next.set(bytes.subarray(0, size), at); files.set(name, next); return size; },
            truncate(n: number) { check(); const next = new Uint8Array(n); next.set(files.get(name)!.subarray(0, n)); files.set(name, next); },
            flush() { check(); flushes++; },
            close() { locked.delete(name); closes++; },
          };
        },
      };
    },
    async removeEntry(name: string) { check(); if (locked.has(name)) throw new DOMException('Busy', 'NoModificationAllowedError'); if (!files.delete(name)) throw new DOMException('Missing', 'NotFoundError'); },
  };
  const nav = { storage: { getDirectory: async () => { check(); return rootDir; } }, onLine: true };
  return { files, nav, locked, set failure(value: string | null) { failure = value; }, set partial(value: number) { partial = value; }, get closes() { return closes; }, get flushes() { return flushes; } };
}

const writerCode = await compile('src/db/opfs-write-worker.ts');
const storeCode = await compile('src/db/opfs-lexicon.ts', '\nexport {opfsAvailable,opfsFileSize,readOpfsFile,removeOpfsFile,writeOpfsFile,resetOpfsProbe} from "./opfs-storage.ts";');
let workers: StorageWorker[] = [];
class StorageWorker extends EventTarget {
  terminated = false;
  workerScope: any;
  constructor(_url: URL) {
    super(); workers.push(this);
    const self = { postMessage: (data: unknown) => this.dispatchEvent(new MessageEvent('message', { data })) };
    this.workerScope = realm(writerCode, { navigator: activeDisk.nav, self });
    this.workerScope.self = self;
  }
  postMessage(message: unknown, transfer: Transferable[] = []) {
    const cloned = structuredClone(message, { transfer });
    void this.workerScope.self.onmessage({ data: cloned });
  }
  terminate() { this.terminated = true; }
}
let activeDisk = disk();
const storage = realm(storeCode, { navigator: activeDisk.nav, Worker: StorageWorker }).subject;
const bytes = Uint8Array.from({ length: 4 * 1024 * 1024 + 7 }, (_, i) => i % 251);
const options = { version: 'v1.1.2-abc', fetchBytes: async () => bytes, expectedByteSize: bytes.length };
const [first, second] = await Promise.all([storage.ensureLexiconInOpfs(options), storage.ensureLexiconInOpfs(options)]);
assert.equal(Number(first.fetched) + Number(second.fetched), 1);
assert.deepEqual(activeDisk.files.get(first.fileName), bytes);
assert.equal(bytes.byteLength, options.expectedByteSize, 'original bytes must not be transferred');
assert.equal(activeDisk.locked.size, 0);
assert(workers.every(w => w.terminated));
assert(!activeDisk.files.has(`${first.fileName}.importing`));
assert.equal(await storage.opfsFileSize('missing'), 0);
for (const name of ['NoModificationAllowedError', 'NotAllowedError', 'QuotaExceededError']) {
  activeDisk.failure = name;
  await assert.rejects(storage.opfsFileSize(first.fileName), { name });
  await assert.rejects(storage.readOpfsFile(first.fileName), { name });
  await assert.rejects(storage.removeOpfsFile(first.fileName), { name });
}
activeDisk.failure = null;
assert.equal(await storage.opfsFileSize(first.fileName), bytes.length, 'transient directory failures remain retryable');

// A failed sync write closes the exclusive handle, leaves a marker, and can be retried.
const failedName = storage.lexiconOpfsFileName('v1.1.2-failed');
// Inject after the handle is opened, via the real worker handler.
const realWriter = realm(writerCode, { navigator: activeDisk.nav }).subject;
await realWriter.handleWriteRequest({ type: 'open', name: failedName });
activeDisk.failure = 'QuotaExceededError';
await assert.rejects(realWriter.handleWriteRequest({ type: 'write', bytes: new Uint8Array([1]), offset: 0 }), { name: 'QuotaExceededError' });
assert.equal(activeDisk.locked.size, 0);
activeDisk.failure = null;
activeDisk.files.set(`${failedName}.importing`, new Uint8Array());
activeDisk.files.set(failedName, new Uint8Array([9, 9, 9, 9]));
await storage.ensureLexiconInOpfs({ version: 'v1.1.2-failed', expectedByteSize: 4, fetchBytes: async () => new Uint8Array([1, 2, 3, 4]) });
assert.deepEqual(activeDisk.files.get(failedName), new Uint8Array([1, 2, 3, 4]));
assert.equal(await storage.readLexiconFromOpfs('unknown'), null);
const other = storage.lexiconOpfsFileName('v1.1.2-other');
activeDisk.files.set(other, new Uint8Array([8]));
await storage.removeLexiconFromOpfs('v1.1.2-failed');
assert(activeDisk.files.has(other), 'purge must retain other identities');

activeDisk = disk(true);
const modern = realm(storeCode, { navigator: activeDisk.nav, Worker: StorageWorker }).subject;
await modern.writeOpfsFile('async.db', new Uint8Array([5, 6, 7]));
assert.deepEqual(activeDisk.files.get('async.db'), new Uint8Array([5, 6, 7]));
assert.equal(activeDisk.closes, 1);

const backendCode = await compile('src/db/opfs-vfs-backend.ts');
const rpcWorkers: RpcWorker[] = [];
class RpcWorker extends EventTarget {
  terminated = false;
  ignoreClose = false;
  constructor(_url: URL) { super(); rpcWorkers.push(this); }
  postMessage(message: any) {
    if (message.type === 'init') queueMicrotask(() => this.dispatchEvent(new MessageEvent('message', { data: { id: message.id, type: 'init-ok', fileName: message.fileName, byteSize: 4, fetched: false } })));
    if (message.type === 'close' && !this.ignoreClose) queueMicrotask(() => this.dispatchEvent(new MessageEvent('message', { data: { id: message.id, type: 'close-ok' } })));
  }
  terminate() { this.terminated = true; }
}
const backend = realm(backendCode, { Worker: RpcWorker }).subject;
const opened = await backend.openOpfsVfsDatabase({ version: 'v1.1.2', fetchUrl: '/db' });
const pending = opened.db.query('SELECT 1', []);
const rejected = assert.rejects(pending, { name: 'AbortError' });
await backend.resetOpfsVfsWorker(); await rejected;
assert(rpcWorkers.at(-1)!.terminated);
assert.equal(backend.getOpfsVfsWorkerDebugState().pending.length, 0);
for (const event of ['messageerror', 'error']) {
  const next = await backend.openOpfsVfsDatabase({ version: 'v1.1.2', fetchUrl: '/db' });
  const rejected = assert.rejects(next.db.query('SELECT 1', []));
  rpcWorkers.at(-1)!.dispatchEvent(new Event(event)); await rejected;
  assert(rpcWorkers.at(-1)!.terminated);
}
const stalled = await backend.openOpfsVfsDatabase({ version: 'v1.1.2', fetchUrl: '/db' });
rpcWorkers.at(-1)!.ignoreClose = true;
const started = performance.now(); await stalled.db.close();
assert(performance.now() - started < 2500);
assert(rpcWorkers.at(-1)!.terminated);

// Execute actual ensureSqlite/ensureDbFile with only the WASM boundary stubbed.
let factories = 0;
let failFactory = true;
const wasmGate = defer();
const nativeCode = await compile('src/db/opfs-vfs-worker.ts', '\nexport {ensureSqlite,ensureDbFile};', {
  '@journeyapps/wa-sqlite/dist/wa-sqlite.mjs': 'export default () => globalThis.factory();',
  '@journeyapps/wa-sqlite': 'export const Factory=() => ({vfs_register(){},open_v2:async()=>1,close:async()=>{}}); export const SQLITE_OPEN_READWRITE=2,SQLITE_OPEN_CREATE=4,SQLITE_ROW=100;',
  '@journeyapps/wa-sqlite/src/examples/OPFSCoopSyncVFS.js': 'export const OPFSCoopSyncVFS={create:async()=>({})};',
});
activeDisk = disk();
const native = realm(nativeCode, { navigator: activeDisk.nav, factory: async () => {
  factories++; if (failFactory) throw new Error('Factory failed'); await wasmGate.promise; return {};
}, fetch: async () => new Response(new Uint8Array([1, 2, 3, 4])) }).subject;
await assert.rejects(native.ensureSqlite(), /Factory failed/);
failFactory = false;
const a = native.ensureSqlite(); const b = native.ensureSqlite(); wasmGate.resolve();
assert.equal(await a, await b); assert.equal(factories, 2);
const digest = Buffer.from(await webcrypto.subtle.digest('SHA-256', new Uint8Array([1, 2, 3, 4]))).toString('hex');
const fetched = await native.ensureDbFile('native.db', '/db', false, 4, 4, digest);
assert(fetched.fetched); assert(!activeDisk.files.has('native.db.importing'));
activeDisk.files.set('native.db', new Uint8Array([4, 3, 2, 1]));
assert((await native.ensureDbFile('native.db', '/db', false, 4, 4, digest)).fetched, 'same-size corruption must be rebuilt');
activeDisk.failure = 'NoModificationAllowedError';
await assert.rejects(native.ensureDbFile('native.db', '/db', false, 4, 4), { name: 'NoModificationAllowedError' });
assert.deepEqual(activeDisk.files.get('native.db'), new Uint8Array([1, 2, 3, 4]));
console.log('startup storage recovery self-check ok');

// Real hook retry: rapid clicks coalesce; an old attempt cannot validate or overwrite the new one.
const initStub = `
export const initializeDatabase=()=>globalThis.initCall();
export const resetDatabase=()=>globalThis.resetCall();
export const isLexiconCachedForBackend=async()=>true;
export const getDefaultDbUrl=()=>'/db';
export const isDatabaseInitialized=()=>true;
export const clearOpfsVfsSessionSkip=()=>{};`;
const queryStub = `
export const validateOfflineReadiness=()=>globalThis.validateCall();
export const search=async()=>[],searchPage=async()=>({items:[]}),getDatabaseStats=async()=>({});
export const normalizeQuery=x=>x,parseQuery=x=>x,normalizeAndParse=x=>x;
export const SEARCH_PAGE_SIZE=800,SEARCH_FIRST_PAGE_SIZE=400;
export const searchPageSizeForMode=()=>800,searchLimitForOffset=()=>400;`;
const retryCode = await compile('src/hooks/useDB.ts', '\nexport {useEngineDBState};', {
  react: `export const useState=v=>{const i=globalThis.states.length;globalThis.states.push(typeof v==='function'?v():v);return[globalThis.states[i],v=>{globalThis.states[i]=v}];};
export const useRef=v=>({current:v}),useCallback=f=>f,useMemo=f=>f(),useEffect=()=>{},useLayoutEffect=()=>{},createContext=()=>({}),useContext=()=>null;`,
  '../db/init': initStub, '../db/query': queryStub, '../db/query.ts': queryStub,
  '../db/tail-preload.ts': `export const isStartupComplete=()=>false,startTailPreload=async()=>{},subscribeTailProgress=()=>()=>{};`,
});
const oldInit = defer(); const resetGate = defer();
let initCalls = 0, resetCalls = 0, validationCalls = 0;
const retry = realm(retryCode, { states: [], navigator: { onLine: true },
  initCall: () => ++initCalls === 1 ? oldInit.promise : Promise.resolve(),
  resetCall: () => { resetCalls++; return resetGate.promise; },
  validateCall: async () => { validationCalls++; },
});
const hook = retry.subject.useEngineDBState(true);
const obsolete = hook.initialize(); await Promise.resolve();
const retryOne = hook.retryOfflineReady(); const retryTwo = hook.retryOfflineReady();
assert.equal(resetCalls, 1);
resetGate.resolve(); await Promise.all([retryOne, retryTwo]);
oldInit.resolve(); await obsolete;
assert.equal(initCalls, 2); assert.equal(validationCalls, 1);
assert.equal(retry.states[0], 'ready'); assert.equal(retry.states[5], null);
await hook.initialize(); assert.equal(initCalls, 2, 'ready ref is updated synchronously');

// A successful true query alone cannot claim offline readiness.
const readinessCode = await compile('src/db/query.ts', '', {
  './query-engine': `export const queryEngine={execute:async()=>({items:globalThis.probeRows})};
export const searchWords=()=>{},executeSearch=()=>{},normalizeQuery=x=>x,parseQuery=x=>x,normalizeAndParse=x=>x;`,
  './init': `export const getCurrentLexiconTarget=async()=>({version:'v1.1.2'}),getDatabase=()=>null,
getActiveDbBackendMode=()=>globalThis.mode,getLastLexiconRestoreSource=()=>null,
getLexiconPersistenceError=()=>globalThis.persistError,initializeDatabase=async()=>{},isDatabaseInitialized=()=>true;`,
  './lexicon-restore.ts': 'export const getLexiconCacheStatus=async()=>globalThis.cacheState;',
  './opfs-storage.ts': 'export const opfsAvailable=async()=>true;',
});
const readiness = realm(readinessCode, { mode: 'sqljs', persistError: new DOMException('full', 'QuotaExceededError'),
  probeRows: [{word:'事業'}], cacheState: { opfs: false, swCache: true, any: true } });
await assert.rejects(readiness.subject.validateOfflineReadiness(), /儲存空間不足/);
readiness.persistError = null; readiness.cacheState.opfs = true;
await readiness.subject.validateOfflineReadiness();
readiness.probeRows = [];
await assert.rejects(readiness.subject.validateOfflineReadiness(), /基本查詢無結果/);
console.log('startup retry/readiness self-check ok');

// Both engine realms use the same browser Web Lock; only one imports this identity.
activeDisk.failure = null;
const lockTails = new Map<string, Promise<unknown>>();
Object.assign(activeDisk.nav, { locks: { async request(name: string, work: () => Promise<unknown>) {
  const previous = lockTails.get(name) ?? Promise.resolve();
  const next = previous.catch(() => {}).then(work); lockTails.set(name, next);
  try { return await next; } finally { if (lockTails.get(name) === next) lockTails.delete(name); }
} } });
const cross = realm(storeCode, { navigator: activeDisk.nav, Worker: StorageWorker }).subject;
const crossName = cross.lexiconOpfsFileName('v1.1.2-cross');
const crossResults = await Promise.all([
  native.ensureDbFile(crossName, '/db', false, 4, 4, digest),
  cross.ensureLexiconInOpfs({ version: 'v1.1.2-cross', expectedByteSize: 4, fetchBytes: async () => new Uint8Array([1, 2, 3, 4]) }),
]);
assert.equal(crossResults.filter(r => r.fetched).length, 1);
assert.equal(lockTails.size, 0);

// Actual initialization waits for failed-Worker cleanup and drains cancelled attempts.
const initCode = await compile('src/db/init.ts', '', {
  './opfs-vfs-backend.ts': `export const prewarmOpfsVfsWorker=()=>{};
export const openOpfsVfsDatabase=async()=>{throw new Error('native open failed');};
export const resetOpfsVfsWorker=()=>globalThis.disposeWorker();`,
  './sqljs-backend.ts': 'export const openSqlJsDatabase=()=>globalThis.sqlOpen(),createSqlJsBackend=()=>{};',
  './opfs-storage.ts': 'export const opfsAvailable=async()=>true,resetOpfsProbe=()=>{};',
  './opfs-lexicon.ts': `export const ensureLexiconInOpfs=async()=>({fetched:false,byteSize:4}),
lexiconOpfsFileName=x=>x,readLexiconFromOpfs=async()=>null,removeLexiconFromOpfs=async()=>{};`,
  './lexicon-restore.ts': `export const resolveLexiconBytes=async()=>({bytes:new Uint8Array([1,2,3,4]),source:'network'}),
getLexiconCacheStatus=async()=>({any:true,opfs:true}),purgeStaleLexiconCaches=async()=>{};`,
  './lexicon-manifest.ts': `export const loadLexiconTarget=async()=>({version:'v1.1.2',fetchUrl:'/db'}),
lexiconStorageVersion=x=>x.version,publicAssetUrl=x=>x,lexiconVersionFromEnv=()=> 'v1.1.2';`,
  './db-patch.ts': 'export const applyRuntimeDbPatches=async()=>{},ensureConnectiveCompoundRows=async()=>{},ensureComposedWordRow=async()=>{};',
  './lexicon-length-invariant.ts': 'export class LexiconLengthInvariantError extends Error{};export const assertLexiconLengthInvariant=async()=>{};',
  './phoneme-contract.ts': 'export const phonemeStorageContractOk=async()=>true,assertPhonemeStorageContract=async()=>{};',
  './auxiliary-indexes.ts': 'export const ensureGateAuxiliaryIndexes=async()=>{},resetGateAuxiliaryIndexes=()=>{};',
  './tail-preload.ts': 'export const resetTailPreload=async()=>{};',
});
const disposal = defer(), disposalStarted = defer();
let sqlOpens = 0, databaseCloses = 0;
let sqlWork = async () => { sqlOpens++; return { close: async () => { databaseCloses++; } }; };
const sessionValues = new Map<string,string>();
const initialization = realm(initCode, {
  console: { ...console, warn() {}, log() {} },
  sessionStorage: { getItem: (k:string)=>sessionValues.get(k), setItem:(k:string,v:string)=>sessionValues.set(k,v),removeItem:(k:string)=>sessionValues.delete(k) },
  disposeWorker: () => { disposalStarted.resolve(); return disposal.promise; }, sqlOpen: () => sqlWork(),
});
const firstInitialization = initialization.subject.initializeDatabase();
await disposalStarted.promise;
assert.equal(sqlOpens, 0, 'sql.js must not open before failed Worker disposal');
disposal.resolve(); await firstInitialization;
assert.equal(sqlOpens, 1);
await initialization.subject.resetDatabase();
const slowSql = defer(), slowStarted = defer();
let old = true;
sqlWork = async () => {
  sqlOpens++;
  if (old) { old=false; slowStarted.resolve(); await slowSql.promise; }
  return { close: async () => { databaseCloses++; } };
};
const staleInitialization = initialization.subject.initializeDatabase();
const cancelled = assert.rejects(staleInitialization, { name: 'AbortError' });
await slowStarted.promise;
const clearing = initialization.subject.resetDatabase();
const newInitialization = initialization.subject.initializeDatabase();
slowSql.resolve();
await clearing; await cancelled; await newInitialization;
assert(initialization.subject.isDatabaseInitialized());
assert(databaseCloses >= 2, 'cancelled/superseded DB connections must close');
console.log('startup cross-backend/init cancellation self-check ok');
