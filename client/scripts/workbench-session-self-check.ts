/**
 * WorkbenchSession: single root for 句稿 + 替換條件; derivePlan on read; full-session undo; storage migrate.
 */
import { createLineDraft } from '../src/workbench/line-draft.ts';
import { WORKBENCH_DRAFT_KEY, saveLineDraft } from '../src/workbench/line-draft-storage.ts';
import { parseLineInput } from '../src/workbench/line-input.ts';
import {
  WORKBENCH_SESSION_KEY,
  clearWorkbenchSession,
  derivePlan,
  derivePlanBase,
  emptySession,
  loadWorkbenchSession,
  saveWorkbenchSession,
  sessionFromDraft,
  sessionReducer,
  sessionToggleLock,
  type WorkbenchSession,
} from '../src/workbench/session/index.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench session: ${message}`);
}

function memStorage(): {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
} {
  const map = new Map<string, string>();
  return {
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => { map.set(k, v); },
    removeItem: (k) => { map.delete(k); },
  };
}

const parsed = parseLineInput('我愛香港');
assert(parsed.ok, 'parse sentence');
let session: WorkbenchSession = sessionReducer(emptySession(), {
  type: 'create_from_parsed',
  draft: createLineDraft(parsed),
});
assert(session.draft?.slots.length === 4, 'draft slots');
assert(session.version >= 1, 'version bumped');
assert(session.constraints.codeConstraint === 'same_tone', 'default code mode');

// lock span 2..3
let lock = sessionToggleLock(session, 2);
assert(lock.ok, 'lock pos 2');
session = lock.session;
lock = sessionToggleLock(session, 3);
assert(lock.ok, 'lock pos 3');
session = lock.session;
assert(session.draft?.selection?.start === 2 && session.draft.selection.width === 2, 'span from locks');

// readings so same_tone has codes when locked
session = sessionReducer(session, { type: 'choose_reading', pos: 2, jyutping: 'hoeng1', code: '3' });
session = sessionReducer(session, { type: 'choose_reading', pos: 3, jyutping: 'gong2', code: '9' });

const planBase = derivePlanBase(session);
assert(planBase, 'plan base with selection');
assert(planBase!.selectionVersion === session.version, 'plan uses session.version');
assert(planBase!.width === 2, 'plan width');
assert(planBase!.slots.some((s) => s.kind === 'code_digit'), 'same_tone injects codes');

const plan = derivePlan(session, { offset: 10, limit: 50 });
assert(plan?.offset === 10 && plan.limit === 50, 'paging is parameter only');
assert(!('offset' in (session as object) && (session as { offset?: number }).offset === 10), 'session has no offset field');

// mode change bumps version; no planKey
const vBefore = session.version;
session = sessionReducer(session, { type: 'set_mode', mode: 'm2' });
assert(session.version === vBefore + 1, 'mode bumps version');
assert(session.constraints.mode === 'm2', 'mode stored in constraintsUI');
assert(derivePlanBase(session)?.mode === 'm2', 'derive reads mode');

// rhyme picks write phoneme via single path
session = sessionReducer(session, {
  type: 'set_rhyme_picks',
  picks: { whole: true, head: false, tail: false, middles: [] },
});
// need readings on slots for anchors
assert(
  session.draft?.constraints.some((c) => c.kind === 'final_anchor')
    || session.draft?.slots[2]?.reading,
  'phoneme path runs (anchors if reading present)',
);

// apply candidate undo is full session
const beforeApply = session;
session = sessionReducer(session, {
  type: 'apply_candidate',
  selectionVersion: session.version,
  literal: '香江',
  jyutping: 'hoeng1 gong1',
  code: '33',
});
assert(session.draft?.surface.includes('香江') || session.draft?.slots.slice(2, 4).map((s) => s.surface).join('') === '香江', 'candidate applied');
assert(session.undo, 'undo snapshot after apply');
session = sessionReducer(session, { type: 'undo' });
assert(session.constraints.mode === beforeApply.constraints.mode, 'undo restores constraints');
assert(session.draft?.slots[2]?.surface === beforeApply.draft?.slots[2]?.surface, 'undo restores draft');

// clear + undo
session = sessionReducer(session, { type: 'set_mode', mode: 'm3' });
session = sessionReducer(session, { type: 'clear' });
assert(session.draft === null, 'cleared');
assert(session.undo, 'clear keeps undo');
session = sessionReducer(session, { type: 'undo' });
assert(session.draft, 'undo clear restores draft');
assert(session.constraints.mode === 'm3', 'undo clear restores mode');

// storage session round-trip
const store = memStorage();
saveWorkbenchSession(store, session);
const loaded = loadWorkbenchSession(store);
assert(loaded?.draft?.surface === session.draft?.surface, 'session persist surface');
assert(loaded?.constraints.mode === session.constraints.mode, 'session persist mode');
assert(loaded?.version === session.version, 'session persist version');

// migrate legacy draft key
const store2 = memStorage();
const legacyParsed = parseLineInput('香港');
assert(legacyParsed.ok, 'legacy parse');
const legacyDraft = createLineDraft(legacyParsed);
saveLineDraft(store2, legacyDraft);
assert(store2.getItem(WORKBENCH_DRAFT_KEY), 'legacy key written');
const migrated = loadWorkbenchSession(store2);
assert(migrated?.draft?.surface === '香港', 'migrate draft → session');
assert(migrated?.constraints.codeConstraint === 'same_tone', 'migrate defaults constraints');

// clear storage
clearWorkbenchSession(store);
assert(!store.getItem(WORKBENCH_SESSION_KEY), 'session key cleared');

// sessionFromDraft helper
const fromDraft = sessionFromDraft(legacyDraft);
assert(fromDraft.draft?.surface === '香港' && fromDraft.version >= 1, 'sessionFromDraft');

console.log('workbench-session-self-check: ok');
