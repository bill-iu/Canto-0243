import {
  buildPhonemeAnchors,
  emptyPhonemeDimPicks,
  replacementSpanFromLocks,
  sanitizePhonemeDimPicks,
  spanPositionOptions,
  toggleLockKeepingSpan,
} from '../src/workbench/replacement-span.ts';
import { createLineDraft, lineDraftReducer } from '../src/workbench/line-draft.ts';
import { parseLineInput } from '../src/workbench/line-input.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`replacement-span: ${message}`);
}

const parsed = parseLineInput('我愛香港山水');
assert(parsed.ok, 'fixture');
let draft = createLineDraft(parsed);

assert(replacementSpanFromLocks(draft.slots) == null, 'empty locks must yield null span');

let result = toggleLockKeepingSpan(draft, 0);
assert(result.ok && result.draft.selection?.width === 1, 'single lock span');
draft = result.draft;

result = toggleLockKeepingSpan(draft, 4);
assert(!result.ok && result.reason === 'span_too_wide', 'span >4 must reject');

result = toggleLockKeepingSpan(draft, 1);
assert(result.ok && result.draft.selection?.width === 2, 'adjacent lock grows span');
draft = result.draft;

result = toggleLockKeepingSpan(draft, 5);
assert(!result.ok && result.reason === 'span_too_wide', 'distant lock must reject');

const blank = parseLineInput('39');
assert(blank.ok && blank.kind === 'code', 'code fixture');
let codeDraft = createLineDraft(blank);
result = toggleLockKeepingSpan(codeDraft, 0);
assert(!result.ok && result.reason === 'no_surface', 'blank surface cannot lock');

assert(spanPositionOptions(1).length === 1, 'width 1 options');
assert(spanPositionOptions(4).some((o) => o.key === 1) && spanPositionOptions(4).some((o) => o.key === 2), 'width 4 middles');

const picks = sanitizePhonemeDimPicks({ whole: false, head: true, tail: true, middles: [1, 2] }, 2);
assert(picks.middles.length === 0 && picks.head && picks.tail, 'sanitize drops invalid middles');

draft = lineDraftReducer(createLineDraft(parsed), { type: 'select', start: 2, width: 2 });
result = toggleLockKeepingSpan(draft, 2);
assert(result.ok);
draft = result.draft;
result = toggleLockKeepingSpan(draft, 3);
assert(result.ok);
draft = result.draft;
draft = lineDraftReducer(draft, { type: 'choose_reading', pos: 2, jyutping: 'hoeng1', code: '3' });
draft = lineDraftReducer(draft, { type: 'choose_reading', pos: 3, jyutping: 'gong2', code: '9' });
const anchors = buildPhonemeAnchors(
  draft.selection!,
  draft.slots,
  { whole: true, head: false, tail: false, middles: [] },
  emptyPhonemeDimPicks(),
);
assert(anchors.length === 2 && anchors.every((a) => a.kind === 'final_anchor'), 'whole rhyme anchors');
assert(anchors.map((a) => a.refJyutping).join(' ') === 'hoeng1 gong2', 'anchors keep selected readings');

console.log('replacement-span self-check ok');
