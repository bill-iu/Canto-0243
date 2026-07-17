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

console.log('workbench adapter self-check ok');
