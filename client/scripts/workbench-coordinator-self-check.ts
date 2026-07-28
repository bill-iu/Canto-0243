import { parseLineInput } from '../src/workbench/line-input.ts';
import { createLineDraft } from '../src/workbench/line-draft.ts';
import { resetPosFilter } from '../src/pos/filter.ts';
import {
  createWorkbenchCoordinatorState,
  workbenchCoordinatorReducer,
} from '../src/workbench/workbench-coordinator.ts';
import { defaultConstraintsUI } from '../src/workbench/session/defaults.ts';
import { createTouchGestureState, reduceTouchGesture } from '../src/workbench/touch-gesture.ts';
import { WorkbenchReadingLifecycle } from '../src/workbench/workbench-reading-lifecycle.ts';
import type { WorkbenchAdapter } from '../src/workbench/workbench-adapter.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench coordinator: ${message}`);
}

const parsed = parseLineInput('香港人');
assert(parsed.ok, 'seed line');
const draft = createLineDraft(parsed);
const initial = {
  draft,
  constraints: defaultConstraintsUI(),
  version: 1,
  undo: null,
};
let state = createWorkbenchCoordinatorState(initial, resetPosFilter());

const lock0 = workbenchCoordinatorReducer(state, { type: 'session', action: { type: 'toggle_lock', pos: 0 } });
assert(lock0.session.version === 2 && lock0.session.draft?.slots[0]?.locked, 'lock transition');
const lock1 = workbenchCoordinatorReducer(lock0, { type: 'session', action: { type: 'toggle_lock', pos: 1 } });
assert(lock1.session.version === 3 && lock1.session.draft?.slots[1]?.locked, 'rapid lock transition');

const preview = workbenchCoordinatorReducer(lock1, {
  type: 'set_preview',
  version: lock1.session.version,
  preview: null,
});
assert(preview.preview === null, 'preview set');
const stalePreview = workbenchCoordinatorReducer(preview, {
  type: 'set_preview',
  version: 1,
  preview: null,
});
assert(stalePreview === preview, 'stale preview ignored');

const oldReading = workbenchCoordinatorReducer(lock1, {
  type: 'reading_resolved',
  version: lock1.session.version - 1,
  readings: [],
  autoChoices: [],
});
assert(oldReading === lock1, 'stale reading ignored');

let gesture = createTouchGestureState();
let result = reduceTouchGesture(gesture, { type: 'down', pointerId: 1, pos: 0, x: 10, y: 10, at: 0 });
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'up', pointerId: 1, pos: 0, x: 10, y: 10, at: 10 });
assert(result.intent?.type === 'lock' && result.intent.pos === 0, 'first touch locks');
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'down', pointerId: 2, pos: 1, x: 30, y: 10, at: 100 });
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'up', pointerId: 2, pos: 1, x: 30, y: 10, at: 110 });
assert(result.intent?.type === 'lock' && result.intent.pos === 1, 'A then B locks both');
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'down', pointerId: 3, pos: 0, x: 10, y: 10, at: 150 });
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'up', pointerId: 3, pos: 0, x: 10, y: 10, at: 160 });
assert(result.intent?.type === 'lock' && result.intent.pos === 0, 'A after B is not edit');
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'down', pointerId: 4, pos: 0, x: 10, y: 10, at: 200 });
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'up', pointerId: 4, pos: 0, x: 10, y: 10, at: 210 });
assert(result.intent?.type === 'edit' && result.intent.pos === 0, 'same-cell touch double tap edits');

gesture = createTouchGestureState();
result = reduceTouchGesture(gesture, { type: 'down', pointerId: 5, pos: 0, x: 10, y: 10, at: 0 });
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'down', pointerId: 6, pos: 1, x: 30, y: 10, at: 1 });
gesture = result.state;
result = reduceTouchGesture(gesture, { type: 'up', pointerId: 5, pos: 0, x: 10, y: 10, at: 10 });
assert(result.intent === null, 'multi-touch first completion is ignored');
result = reduceTouchGesture(result.state, { type: 'up', pointerId: 6, pos: 1, x: 30, y: 10, at: 11 });
assert(result.intent === null, 'multi-touch second completion is ignored');

let readingSignal: AbortSignal | undefined;
const readingAdapter: WorkbenchAdapter = {
  resolveLine(_surface, signal) {
    readingSignal = signal;
    return new Promise((_resolve, reject) => {
      signal?.addEventListener(
        'abort',
        () => reject(new DOMException('Aborted', 'AbortError')),
        { once: true },
      );
    });
  },
  async findCandidates() {
    throw new Error('unused');
  },
};
const lifecycle = new WorkbenchReadingLifecycle(readingAdapter);
const pendingReading = lifecycle.resolveLine(1, [{ surface: '香' }], []);
lifecycle.setActive(false);
await pendingReading.then(
  () => { throw new Error('inactive reading resolved'); },
  (error) => assert(error instanceof DOMException && error.name === 'AbortError', 'inactive reading abort'),
);
assert(readingSignal?.aborted, 'inactive coordinator must abort its reading request');

console.log('workbench coordinator self-check ok');
