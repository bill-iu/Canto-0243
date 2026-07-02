/**
 * DB-5 cold-start / memory / probe-query benchmark — ADR-0024 §7.2
 * ponytail: Chrome exposes performance.memory; Safari → Web Inspector manual M4
 */
import type { DbBackendMode } from './db-backend-mode.ts';
import {
  getDbBackendMode,
  getDefaultDbUrl,
  getLexiconCacheStatus,
  initializeDatabase,
  resetDatabase,
  type LexiconCacheStatus,
} from './init.ts';
import {
  OFFLINE_READINESS_PROBE_QUERY,
  search,
  validateOfflineReadiness,
} from './query.ts';

export type DbBenchmarkMemory = {
  heapUsedMb: number | null;
  heapTotalMb: number | null;
};

export type DbBenchmarkSample = {
  backend: DbBackendMode;
  lexiconVersion: string;
  dbUrl: string;
  online: boolean;
  cache: LexiconCacheStatus;
  initMs: number;
  probeQueryMs: number;
  totalMs: number;
  memoryAfterInit: DbBenchmarkMemory;
  memoryAfterProbe: DbBenchmarkMemory;
  storageUsageMb: number | null;
  storageQuotaMb: number | null;
  probeQuery: string;
  probeWord: string | null;
  ok: boolean;
};

function lexiconVersion(): string {
  return (import.meta as ImportMeta).env?.VITE_LEXICON_VERSION || 'dev';
}

function readJsHeap(): DbBenchmarkMemory {
  const mem = (
    performance as Performance & {
      memory?: { usedJSHeapSize: number; totalJSHeapSize: number };
    }
  ).memory;
  if (!mem) {
    return { heapUsedMb: null, heapTotalMb: null };
  }
  const toMb = (n: number) => Math.round((n / 1024 / 1024) * 10) / 10;
  return { heapUsedMb: toMb(mem.usedJSHeapSize), heapTotalMb: toMb(mem.totalJSHeapSize) };
}

async function readStorageEstimate(): Promise<{ usageMb: number | null; quotaMb: number | null }> {
  if (!navigator.storage?.estimate) {
    return { usageMb: null, quotaMb: null };
  }
  try {
    const { usage, quota } = await navigator.storage.estimate();
    const toMb = (n?: number) =>
      typeof n === 'number' ? Math.round((n / 1024 / 1024) * 10) / 10 : null;
    return { usageMb: toMb(usage), quotaMb: toMb(quota) };
  } catch {
    return { usageMb: null, quotaMb: null };
  }
}

/** ponytail: self-check / copy-paste friendly one-liner */
export function formatBenchmarkSample(sample: DbBenchmarkSample): string {
  return JSON.stringify(sample, null, 2);
}

/**
 * Run init + probe query benchmark. Call with resetFirst for cold-init timing.
 */
export async function runDbBenchmark(opts?: { resetFirst?: boolean }): Promise<DbBenchmarkSample> {
  const t0 = performance.now();
  if (opts?.resetFirst) {
    resetDatabase();
  }

  const version = lexiconVersion();
  const dbUrl = getDefaultDbUrl();
  const cache = await getLexiconCacheStatus(version, dbUrl);

  const tInit0 = performance.now();
  await initializeDatabase(dbUrl);
  await validateOfflineReadiness();
  const initMs = Math.round(performance.now() - tInit0);
  const memoryAfterInit = readJsHeap();

  const tProbe0 = performance.now();
  const results = await search({
    query: OFFLINE_READINESS_PROBE_QUERY,
    mode: '0243',
    limit: 1,
  });
  const probeQueryMs = Math.round(performance.now() - tProbe0);
  const memoryAfterProbe = readJsHeap();
  const storage = await readStorageEstimate();

  return {
    backend: getDbBackendMode(),
    lexiconVersion: version,
    dbUrl,
    online: navigator.onLine,
    cache,
    initMs,
    probeQueryMs,
    totalMs: Math.round(performance.now() - t0),
    memoryAfterInit,
    memoryAfterProbe,
    storageUsageMb: storage.usageMb,
    storageQuotaMb: storage.quotaMb,
    probeQuery: OFFLINE_READINESS_PROBE_QUERY,
    probeWord: results[0]?.word ?? null,
    ok: Boolean(results[0]?.word),
  };
}
