import assert from 'node:assert/strict';
import { createLineDraft } from '../src/workbench/line-draft.ts';
import { parseLineInput } from '../src/workbench/line-input.ts';
import { sessionFromDraft } from '../src/workbench/session/defaults.ts';
import { sessionReducer } from '../src/workbench/session/reducer.ts';
import {
  WORKBENCH_SESSION_KEY, WORKBENCH_SESSION_RECOVERY_KEY, clearWorkbenchSession,
  exportWorkbenchSession, importWorkbenchSession, loadWorkbenchSession, saveWorkbenchSession,
} from '../src/workbench/session/storage.ts';

const values = new Map<string, string>();
const storage = { getItem: (key: string) => values.get(key) ?? null,
  setItem: (key: string, value: string) => { values.set(key, value); },
  removeItem: (key: string) => { values.delete(key); } };
const parsed = parseLineInput('我愛香港');
assert(parsed.ok);
let session = sessionFromDraft(createLineDraft(parsed));
session = sessionReducer(session, { type: 'choose_reading', pos: 2, jyutping: 'hoeng1', code: '3' });
session = sessionReducer(session, { type: 'toggle_lock', pos: 2 });
session = sessionReducer(session, { type: 'replace_surface', literal: '我愛海港' });
// JSON intentionally omits optional undefined fields.
session = JSON.parse(JSON.stringify(session));
const backup = exportWorkbenchSession(session);
const document = JSON.parse(backup);
assert.equal(document.version, 2);
assert(!('locked' in document.content.slots[0]));
assert(!('surface' in document.editor.draft));
assert.deepEqual(importWorkbenchSession(storage, backup), session);
assert.deepEqual(loadWorkbenchSession(storage), session);
assert.deepEqual(sessionReducer(loadWorkbenchSession(storage)!, { type: 'undo' }),
  sessionReducer(session, { type: 'undo' }));

values.set(WORKBENCH_SESSION_KEY, JSON.stringify({ version: 1, session }));
const migrated = loadWorkbenchSession(storage)!;
assert.deepEqual(migrated, session);
saveWorkbenchSession(storage, migrated);
assert.equal(JSON.parse(values.get(WORKBENCH_SESSION_KEY)!).version, 2);
const previous = values.get(WORKBENCH_SESSION_KEY);
for (const invalid of ['{', '{"version":999}', JSON.stringify({ ...document, content: null }),
  JSON.stringify({ ...document, editor: { ...document.editor, draft: { ...document.editor.draft, locks: [] } } })]) {
  assert.throws(() => importWorkbenchSession(storage, invalid));
  assert.equal(values.get(WORKBENCH_SESSION_KEY), previous);
}
const full = { ...storage, setItem: () => { throw new Error('quota'); } };
assert.throws(() => saveWorkbenchSession(full, session), /quota/);
assert.throws(() => importWorkbenchSession(full, backup), /quota/);
assert.equal(values.get(WORKBENCH_SESSION_KEY), previous);
for (const unreadable of ['{broken', '{"version":999}']) {
  values.set(WORKBENCH_SESSION_KEY, unreadable);
  assert.equal(loadWorkbenchSession(storage), null);
  assert.equal(values.get(WORKBENCH_SESSION_RECOVERY_KEY), unreadable);
  assert.throws(() => saveWorkbenchSession(storage, session));
  assert.throws(() => clearWorkbenchSession(storage));
  assert.equal(values.get(WORKBENCH_SESSION_KEY), unreadable);
}
assert.deepEqual(importWorkbenchSession(storage, backup), session);
assert.equal(values.get(WORKBENCH_SESSION_RECOVERY_KEY), '{"version":999}');
const draftV1 = JSON.stringify({ version: 1, draft: session.draft });
assert.equal(importWorkbenchSession(storage, draftV1).draft?.surface, session.draft?.surface);
console.log('workbench document: migration, content/editor separation, undo, backup and failure preservation ok');
