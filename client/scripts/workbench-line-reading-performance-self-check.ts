import type { PwaLineReadingSlot } from '../src/workbench/pwa-line-readings.ts';
import { createLineReadingResolver } from '../src/workbench/line-reading-cache.ts';
import { LineReadingCoordinator } from '../src/workbench/line-reading-coordinator.ts';
import type { WorkbenchAdapter } from '../src/workbench/workbench-adapter.ts';

const slot = (
  surface: string,
  jyutping = '',
  code = '',
): PwaLineReadingSlot => ({
  surface,
  kind: jyutping ? 'resolved' : 'unresolved',
  choices: jyutping ? [{ jyutping, code, initial: jyutping[0] ?? '', final: jyutping.slice(1) }] : [],
  needsChoice: false,
});

let loads = 0;
const requested: string[] = [];
const resolver = createLineReadingResolver('v1', async (surface) => {
  loads += 1;
  requested.push(surface);
  return Array.from(surface, (literal) => (
    literal === '𠮶' ? slot(literal) : slot(literal, `${literal}1`, '3')
  ));
}, 2);

const first = await resolver.resolve('香香𠮶');
const second = await resolver.resolve('香𠮶');
if (first.length !== 3 || second.length !== 2 || loads !== 1 || requested[0] !== '香𠮶') {
  throw new Error(`literal cache/dedupe failed: loads=${loads} requested=${requested.join('|')}`);
}

await resolver.resolve('港');
await resolver.resolve('你');
await resolver.resolve('香');
if (loads !== 4) throw new Error(`bounded LRU did not evict oldest literal: ${loads}`);

let release!: () => void;
const gate = new Promise<void>((resolve) => { release = resolve; });
let coalescedLoads = 0;
const coalesced = createLineReadingResolver('v1', async (surface) => {
  coalescedLoads += 1;
  await gate;
  return Array.from(surface, (literal) => slot(literal, `${literal}1`, '3'));
});
const coalescedOne = coalesced.resolve('香港');
const coalescedTwo = coalesced.resolve('香港');
release();
await Promise.all([coalescedOne, coalescedTwo]);
if (coalescedLoads !== 1) throw new Error(`identical in-flight requests did not coalesce: ${coalescedLoads}`);

let releaseShared!: () => void;
const sharedGate = new Promise<void>((resolve) => { releaseShared = resolve; });
let sharedSignal: AbortSignal | undefined;
const shared = createLineReadingResolver('v1', async (surface, signal) => {
  sharedSignal = signal;
  await sharedGate;
  return Array.from(surface, (literal) => slot(literal, `${literal}1`, '3'));
});
const cancelledCaller = new AbortController();
const cancelledWait = shared.resolve('難', cancelledCaller.signal);
const survivingWait = shared.resolve('難');
cancelledCaller.abort();
releaseShared();
try {
  await cancelledWait;
  throw new Error('cancelled coalesced caller resolved');
} catch (error) {
  if (!(error instanceof DOMException) || error.name !== 'AbortError') throw error;
}
await survivingWait;
if (sharedSignal?.aborted) throw new Error('one caller aborted a batch still needed by another caller');

const calls: Array<{ surface: string; signal?: AbortSignal }> = [];
const adapter: WorkbenchAdapter = {
  resolveLine(surface, signal) {
    calls.push({ surface, signal });
    return new Promise((resolve, reject) => {
      signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
      if (surface === '港') resolve([slot('港', 'gong2', '9')]);
    });
  },
  async findCandidates() {
    throw new Error('unused');
  },
};
const coordinator = new LineReadingCoordinator(adapter);
const oldRequest = coordinator.resolve(1, [{ surface: '香' }]);
const latest = await coordinator.resolve(2, [
  { surface: '香', reading: 'manual1', code: '7' },
  { surface: '港' },
]);
try {
  await oldRequest;
  throw new Error('superseded reading request resolved');
} catch (error) {
  if (!(error instanceof DOMException) || error.name !== 'AbortError') throw error;
}
if (!calls[0]?.signal?.aborted) throw new Error('superseded request was not truly cancelled');
if (latest.version !== 2 || latest.autoChoices.length !== 1 || latest.autoChoices[0]?.pos !== 1) {
  throw new Error('coordinator overwrote a manual reading or missed the changed slot');
}

console.log('workbench line reading performance self-check ok');
