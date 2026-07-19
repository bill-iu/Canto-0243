import {
  createResumeDebugBuffer,
  isResumeDebugEnabled,
  recordResumeDebug,
  type ResumeDebugDetail,
} from '../src/resume-debug.ts';

if (isResumeDebugEnabled()) {
  throw new Error('resume-debug-self-check: Node must default disabled');
}
recordResumeDebug('disabled-noop', { value: 1 });

let now = 0;
const buffer = createResumeDebugBuffer({
  now: () => now++,
  getVisibilityState: () => 'visible',
  getBackendMode: () => 'opfs-vfs',
  getWorkerState: () => ({
    exists: true,
    pending: [{ id: 7, type: 'query', ageMs: 50 }],
  }),
  limit: 200,
});

for (let i = 0; i < 205; i += 1) {
  buffer.record('tick', { i });
}
if (buffer.state.events.length !== 200 || buffer.state.events[0]?.detail.i !== 5) {
  throw new Error('resume-debug-self-check: ring buffer bound/order');
}

const snapshot = buffer.state.snapshot();
snapshot.events[0]!.detail.i = -1;
snapshot.worker.pending[0]!.ageMs = -1;
if (
  buffer.state.events[0]?.detail.i !== 5 ||
  buffer.state.snapshot().worker.pending[0]?.ageMs !== 50
) {
  throw new Error('resume-debug-self-check: snapshot must be isolated');
}

let rejectedNested = false;
try {
  buffer.record('invalid', { nested: [] } as unknown as ResumeDebugDetail);
} catch (error) {
  rejectedNested = error instanceof TypeError;
}
if (!rejectedNested) {
  throw new Error('resume-debug-self-check: nested detail accepted');
}

console.log('resume-debug-self-check ok');
