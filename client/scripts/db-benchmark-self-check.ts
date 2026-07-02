/** ponytail: DB-5 — formatBenchmarkSample round-trip */
import {
  formatBenchmarkSample,
  type DbBenchmarkSample,
} from '../src/db/db-benchmark.ts';

const mock: DbBenchmarkSample = {
  backend: 'sqljs',
  lexiconVersion: 'dev',
  dbUrl: '/lyrics.dev.db',
  online: true,
  cache: { opfs: false, swCache: true, any: true },
  initMs: 1200,
  probeQueryMs: 45,
  totalMs: 1300,
  memoryAfterInit: { heapUsedMb: 180.5, heapTotalMb: 220 },
  memoryAfterProbe: { heapUsedMb: 182.1, heapTotalMb: 220 },
  storageUsageMb: 106,
  storageQuotaMb: 4096,
  probeQuery: '事業',
  probeWord: '事業',
  ok: true,
};

const json = formatBenchmarkSample(mock);
const parsed = JSON.parse(json) as DbBenchmarkSample;
if (parsed.initMs !== 1200 || !parsed.ok) {
  throw new Error('db-benchmark-self-check: round-trip');
}
console.log('db-benchmark self-check ok');
