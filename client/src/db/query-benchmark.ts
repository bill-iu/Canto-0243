import type { DatabaseBackend } from './database-backend.ts';
import type { SearchContext, SearchResult } from './query-types.ts';
import { PwaCandidateSnapshotStore } from '../workbench/pwa-candidate-snapshot.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from '../workbench/contracts.ts';

export const BENCHMARK_QUERIES = [
  { id: 'lookup', q: '香港', rhyme_profile: 'exact' },
  { id: 'dense-code', q: '30', rhyme_profile: 'exact' },
  { id: 'wildcard', q: '香??', rhyme_profile: 'exact' },
  { id: 'rhyme-exact', q: '香港=', rhyme_profile: 'exact' },
  { id: 'rhyme-loose', q: '香港=', rhyme_profile: 'tong' },
] as const;

export interface QueryBenchmarkSample {
  id: string;
  phase: 'first' | 'repeat';
  elapsedMs: number;
  items: number;
  total: number | null;
  maxEventLoopDelayMs: number;
  sampledHeapPeakBytes: number | null;
}

/** Timer delay is an event-loop diagnostic, not a browser Long Tasks measurement. */
async function measure(
  id: string,
  phase: QueryBenchmarkSample['phase'],
  run: () => Promise<{ items: number; total?: number }>,
  heapBytes: () => number | null,
): Promise<QueryBenchmarkSample> {
  let peak = heapBytes();
  let lag = 0;
  let previous = performance.now();
  const timer = setInterval(() => {
    const now = performance.now();
    lag = Math.max(lag, now - previous - 10);
    previous = now;
    const heap = heapBytes();
    if (heap !== null) peak = Math.max(peak ?? 0, heap);
  }, 10);
  try {
    const start = performance.now();
    const result = await run();
    const elapsedMs = performance.now() - start;
    const heap = heapBytes();
    if (heap !== null) peak = Math.max(peak ?? 0, heap);
    // Let an overdue timer observe synchronous query/sort blocking.
    await new Promise((resolve) => setTimeout(resolve, 0));
    return { id, phase, elapsedMs, ...result, total: result.total ?? null,
      maxEventLoopDelayMs: Math.max(0, lag), sampledHeapPeakBytes: peak };
  } finally {
    clearInterval(timer);
  }
}

/** Same cases can run against a fixture, full sql.js lexicon, or browser backend. */
export async function runQueryBenchmark(
  db: DatabaseBackend,
  search: (context: SearchContext) => Promise<SearchResult>,
  heapBytes: () => number | null = () => null,
  findCandidates?: (plan: ReplacementPlanV1) => Promise<WorkbenchCandidateResponse>,
): Promise<QueryBenchmarkSample[]> {
  const samples: QueryBenchmarkSample[] = [];
  for (const query of BENCHMARK_QUERIES) {
    for (const phase of ['first', 'repeat'] as const) {
      samples.push(await measure(query.id, phase, async () => {
        const result = await search({ ...query, mode: 'm1', offset: 0, limit: 400 });
        return { items: result.items.length, total: result.total };
      }, heapBytes));
    }
  }
  for (const width of [2, 4]) {
    const store = new PwaCandidateSnapshotStore();
    const plan: ReplacementPlanV1 = { version: 1, selectionVersion: 1, width,
      mode: 'm1', semanticIntent: 'off', slots: [], offset: 0, limit: 400 };
    for (const phase of ['first', 'repeat'] as const) {
      samples.push(await measure(`workbench-unanchored-${width}`, phase, async () => {
        const result = await (findCandidates ? findCandidates(plan) : store.page(plan, db));
        return { items: Object.values(result.exact).reduce((n, rows) => n + rows.length, 0),
          total: result.engineTotal };
      }, heapBytes));
    }
  }
  return samples;
}
