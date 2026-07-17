import { createPortableWorkbenchAdapter } from '../src/workbench/portable-workbench-adapter.ts';
import { WorkbenchAdapterError } from '../src/workbench/workbench-adapter.ts';

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

console.log('workbench adapter self-check ok');
