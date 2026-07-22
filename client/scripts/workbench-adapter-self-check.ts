import { createPortableWorkbenchAdapter } from '../src/workbench/portable-workbench-adapter.ts';
import { createPwaWorkbenchAdapter } from '../src/workbench/pwa-workbench-adapter.ts';
import { WorkbenchAdapterError } from '../src/workbench/workbench-adapter.ts';
import type { ReplacementPlanV1 } from '../src/workbench/contracts.ts';

for (const [status, kind] of [[422, 'invalid_plan'], [503, 'not_ready']] as const) {
  const adapter = createPortableWorkbenchAdapter(async () => new Response('{}', { status }));
  try {
    await adapter.resolveLine('香');
    throw new Error(`status ${status} was accepted`);
  } catch (error) {
    if (!(error instanceof WorkbenchAdapterError) || error.kind !== kind) throw error;
  }
}

const controller = new AbortController();
controller.abort();
const adapter = createPortableWorkbenchAdapter(async (_input, init) => {
  if (init?.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  return new Response('{}');
});
try {
  await adapter.resolveLine('香', controller.signal);
  throw new Error('aborted request resolved');
} catch (error) {
  if (!(error instanceof DOMException) || error.name !== 'AbortError') throw error;
}

// PWA：詞庫未就緒必須係 reject，唔好同步 throw 炸 React effect
const pwa = createPwaWorkbenchAdapter();
const plan: ReplacementPlanV1 = {
  version: 1,
  selectionVersion: 1,
  width: 1,
  mode: 'm1',
  slots: [{ pos: 0, kind: 'code_digit', digit: '3' }],
  semanticIntent: 'off',
  limit: 10,
};
try {
  await pwa.findCandidates(plan);
  throw new Error('pwa findCandidates resolved before lexicon ready');
} catch (error) {
  if (!(error instanceof WorkbenchAdapterError) || error.kind !== 'not_ready') throw error;
}

const snapshotHeaders: Array<string | null> = [];
const portable = createPortableWorkbenchAdapter(async (_input, init) => {
  snapshotHeaders.push(new Headers(init?.headers).get('X-Workbench-Snapshot'));
  const body = JSON.parse(String(init?.body)) as ReplacementPlanV1;
  return new Response(JSON.stringify({
    version: 1,
    selectionVersion: body.selectionVersion,
    exact: { direct_syn: [], semantic_related: [], sound_only: [] },
    total: 0,
    engineTotal: 0,
    relaxation: null,
  }), { headers: { 'X-Workbench-Snapshot': `snapshot-${snapshotHeaders.length}` } });
});
await portable.findCandidates(plan);
await portable.findCandidates({ ...plan, selectionVersion: 2, offset: 10 });
await portable.findCandidates({ ...plan, width: 2, slots: [] });
if (snapshotHeaders.join('|') !== '|snapshot-1|snapshot-2') {
  throw new Error(`opaque snapshot continuity failed: ${snapshotHeaders.join('|')}`);
}

let releaseBuild!: () => void;
const buildGate = new Promise<void>((resolve) => { releaseBuild = resolve; });
let buildCalls = 0;
const coalesced = createPortableWorkbenchAdapter(async (_input, init) => {
  buildCalls += 1;
  await buildGate;
  const body = JSON.parse(String(init?.body)) as ReplacementPlanV1;
  return new Response(JSON.stringify({
    version: 1,
    selectionVersion: body.selectionVersion,
    exact: { direct_syn: [], semantic_related: [], sound_only: [] },
    total: 0,
    engineTotal: 0,
    relaxation: null,
  }), { headers: { 'X-Workbench-Snapshot': 'coalesced' } });
});
const buildOne = coalesced.findCandidates(plan);
const buildTwo = coalesced.findCandidates({ ...plan, selectionVersion: 2 });
releaseBuild();
const [one, two] = await Promise.all([buildOne, buildTwo]);
if (buildCalls !== 1 || one.selectionVersion !== 1 || two.selectionVersion !== 2) {
  throw new Error(`same-identity build did not coalesce: calls=${buildCalls}`);
}

console.log('workbench adapter self-check ok');
