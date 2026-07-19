import { parseLineInput } from '../src/workbench/line-input.ts';
import { createLineDraft, lineDraftReducer } from '../src/workbench/line-draft.ts';
import {
  WORKBENCH_DRAFT_KEY,
  WORKBENCH_RECOVERY_KEY,
  loadLineDraft,
  saveLineDraft,
} from '../src/workbench/line-draft-storage.ts';
import { toggleLockKeepingSpan } from '../src/workbench/replacement-span.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench draft: ${message}`);
}

const surface = parseLineInput('香港');
assert(surface.ok && surface.kind === 'surface', 'sentence was not classified');
assert(surface.slots.map((slot) => slot.surface).join('') === '香港', 'sentence surface changed');
assert(surface.slots.every((slot) => slot.reading == null), 'parser invented readings');

const code = parseLineInput('394052');
assert(code.ok && code.kind === 'code', 'pure code was not classified');
assert(code.slots.every((slot) => slot.surface === ''), 'code input filled text automatically');
assert(code.slots.map((slot) => slot.code).join('') === '394052', 'code slots missing digits');
assert(code.constraints.map((item) => item.digit).join('') === '394052', 'code constraints changed');
assert(createLineDraft(code).slots.every((slot) => slot.code && !slot.surface), 'draft must keep code-only slots');

const tones = parseLineInput('平仄');
assert(tones.ok && tones.kind === 'tone', 'ping/ze input was not classified');
assert(tones.constraints.map((item) => item.toneClass).join(',') === 'ping,ze', 'tone classes changed');

assert(!parseLineInput('香3').ok, 'mixed input was accepted');
assert(!parseLineInput('香'.repeat(65)).ok, 'input beyond 64 slots was accepted');

const parsedSentence = parseLineInput('我愛香港');
assert(parsedSentence.ok, 'valid sentence failed before reducer check');
let draft = createLineDraft(parsedSentence);
const initialVersion = draft.version;
draft = lineDraftReducer(draft, { type: 'select', start: 2, width: 2 });
assert(draft.selection?.start === 2 && draft.selection.width === 2, 'contiguous selection failed');
assert(draft.version === initialVersion + 1, 'selection did not increment version');
assert(lineDraftReducer(draft, { type: 'select', start: 0, width: 5 }) === draft, 'invalid selection changed state');

draft = lineDraftReducer(draft, { type: 'toggle_lock', pos: 0 });
assert(draft.slots[0]?.locked, 'lock toggle failed');
draft = lineDraftReducer(draft, { type: 'choose_reading', pos: 2, jyutping: 'hoeng1', code: '3' });
assert(draft.slots[2]?.reading === 'hoeng1' && draft.slots[2]?.code === '3', 'reading choice failed');
draft = lineDraftReducer(draft, { type: 'set_constraint', constraint: { pos: 3, kind: 'final_anchor', ref: '港' } });
assert(draft.constraints.some((item) => item.kind === 'final_anchor' && item.pos === 3), 'phoneme anchor failed');

const currentVersion = draft.version;
const stale = lineDraftReducer(draft, {
  type: 'apply_candidate',
  selectionVersion: currentVersion - 1,
  literal: '香江',
  jyutping: 'hoeng1 gong1',
  code: '33',
});
assert(stale === draft, 'stale candidate was applied');

draft = lineDraftReducer(draft, {
  type: 'apply_candidate',
  selectionVersion: currentVersion,
  literal: '香江',
  jyutping: 'hoeng1 gong1',
  code: '33',
});
assert(draft.surface === '我愛香江', 'candidate changed more than the selected slice');
assert(draft.lastApplied?.literal === '香江' && draft.undo != null, 'apply metadata or undo missing');
draft = lineDraftReducer(draft, { type: 'undo' });
assert(draft.surface === '我愛香港', 'candidate undo failed');

const beforeRelaxation = draft.constraints;
draft = lineDraftReducer(draft, {
  type: 'apply_relaxation',
  selectionVersion: draft.version,
  relaxationId: 'mode:m3:m2',
  constraints: [{ pos: 2, kind: 'code_digit', digit: '3' }],
});
assert(draft.constraints !== beforeRelaxation && draft.undo != null, 'relaxation was not recorded');
draft = lineDraftReducer(draft, { type: 'undo' });
assert(draft.constraints === beforeRelaxation, 'relaxation undo failed');

draft = lineDraftReducer(draft, { type: 'toggle_lock', pos: 0 });
assert(!draft.slots[0]?.locked, 'cleanup early lock');
draft = lineDraftReducer(draft, { type: 'select', start: 2, width: 2 });
{
  let result = toggleLockKeepingSpan(draft, 2);
  assert(result.ok && result.draft.slots[2]?.locked, 'toggle lock pos 2 failed');
  draft = result.draft;
  result = toggleLockKeepingSpan(draft, 3);
  assert(result.ok && result.draft.slots[3]?.locked && result.draft.selection?.width === 2, 'span from two locks');
  draft = result.draft;
  result = toggleLockKeepingSpan(draft, 2);
  assert(result.ok && !result.draft.slots[2]?.locked && result.draft.selection?.width === 1, 'unlock shrinks span');
  draft = result.draft;
  result = toggleLockKeepingSpan(draft, 2);
  assert(result.ok && result.draft.slots[2]?.locked && result.draft.selection?.width === 2, 're-lock restores span');
  draft = result.draft;
}

const beforeInsert = draft.surface;
draft = lineDraftReducer(draft, { type: 'insert_literal', literal: '香' });
assert(draft.surface === beforeInsert, 'mismatched insert width changed draft');
draft = lineDraftReducer(draft, { type: 'insert_literal', literal: '香江' });
assert(draft.surface === '我愛香江', 'insert_literal failed');
assert(draft.selection?.width === 2 && draft.undo != null, 'insert should keep selection and undo');
draft = lineDraftReducer(draft, { type: 'undo' });
assert(draft.surface === '我愛香港', 'insert undo failed');

const replaced = lineDraftReducer(draft, { type: 'replace_surface', literal: '香江' });
assert(replaced.surface === '香江' && replaced.selection == null && replaced.undo != null, 'replace_surface failed');

const values = new Map<string, string>();
const storage = {
  getItem: (key: string) => values.get(key) ?? null,
  setItem: (key: string, value: string) => { values.set(key, value); },
};
saveLineDraft(storage, draft);
assert(loadLineDraft(storage)?.surface === '我愛香港', 'saved draft did not round-trip');

values.set(WORKBENCH_DRAFT_KEY, '{broken');
assert(loadLineDraft(storage) === null, 'corrupt draft did not fall back');
assert(values.get(WORKBENCH_RECOVERY_KEY) === '{broken', 'corrupt readable payload was not retained');

values.set(WORKBENCH_DRAFT_KEY, JSON.stringify({ version: 2, draft }));
assert(loadLineDraft(storage) === null, 'unknown storage version was accepted');
assert(values.size === 2, 'workbench storage wrote outside its two keys');

console.log('workbench draft self-check ok');
