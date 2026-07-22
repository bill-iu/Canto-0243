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
import {
  emptyPoolTip,
  shouldSkipCandidateQuery,
  WORKBENCH_LEXICON_MAX_WORD_LEN,
  WORKBENCH_PHONEME_MIDDLE_MAX_WIDTH,
} from '../src/workbench/limits.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`replacement-span: ${message}`);
}

const parsed = parseLineInput('我愛香港山水美好歲月');
assert(parsed.ok, 'fixture');
let draft = createLineDraft(parsed);

assert(replacementSpanFromLocks(draft.slots) == null, 'empty locks must yield null span');

let result = toggleLockKeepingSpan(draft, 0);
assert(result.ok && result.draft.selection?.width === 1, 'single lock span');
draft = result.draft;

// ADR-0069: distant locks grow span (was span_too_wide at >4)
result = toggleLockKeepingSpan(draft, 4);
assert(result.ok && result.draft.selection?.width === 5, 'span width 5 allowed');
draft = result.draft;

result = toggleLockKeepingSpan(draft, 9);
assert(result.ok && result.draft.selection?.width === 10, 'full line span allowed');
draft = result.draft;

result = toggleLockKeepingSpan(draft, 1);
assert(result.ok && result.draft.selection?.width === 10, 'inner lock keeps outer span');
draft = result.draft;

const blank = parseLineInput('39');
assert(blank.ok && blank.kind === 'code', 'code fixture');
let codeDraft = createLineDraft(blank);
result = toggleLockKeepingSpan(codeDraft, 0);
assert(result.ok && result.draft.slots[0]?.locked && result.draft.selection?.width === 1, 'code-only slot can lock');
codeDraft = result.draft;
result = toggleLockKeepingSpan(codeDraft, 1);
assert(result.ok && result.draft.selection?.width === 2, 'second code lock grows span');

const emptyParsed = parseLineInput('香港');
assert(emptyParsed.ok, 'empty lock fixture');
const trulyBlank = createLineDraft(emptyParsed);
trulyBlank.slots[0] = { surface: '', locked: false };
result = toggleLockKeepingSpan(trulyBlank, 0);
assert(!result.ok && result.reason === 'no_surface', 'empty slot still cannot lock');

assert(spanPositionOptions(1).length === 1, 'width 1 options');
assert(spanPositionOptions(4).some((o) => o.key === 1) && spanPositionOptions(4).some((o) => o.key === 2), 'width 4 middles');
assert(
  spanPositionOptions(WORKBENCH_PHONEME_MIDDLE_MAX_WIDTH).some((o) => typeof o.key === 'number'),
  'width 6 still has middles',
);
assert(
  !spanPositionOptions(WORKBENCH_PHONEME_MIDDLE_MAX_WIDTH + 1).some((o) => typeof o.key === 'number'),
  'width 7 has no middles',
);

const picks = sanitizePhonemeDimPicks({ whole: false, head: true, tail: true, middles: [1, 2] }, 2);
assert(picks.middles.length === 0 && picks.head && picks.tail, 'sanitize drops invalid middles');

const widePicks = sanitizePhonemeDimPicks(
  { whole: false, head: true, tail: true, middles: [1, 2, 3] },
  8,
);
assert(widePicks.middles.length === 0, 'sanitize drops middles when width > 6');

assert(!shouldSkipCandidateQuery(WORKBENCH_LEXICON_MAX_WORD_LEN), 'width 20 still queries');
assert(shouldSkipCandidateQuery(WORKBENCH_LEXICON_MAX_WORD_LEN + 1), 'width 21 skips');
assert(emptyPoolTip(4, 0) == null, 'width 4 no tip');
assert(emptyPoolTip(5, 1) == null, 'non-empty no tip');
assert(Boolean(emptyPoolTip(5, 0)), 'sparse tip');
assert(Boolean(emptyPoolTip(21, 0)), 'structural tip');
assert(emptyPoolTip(21, 0) !== emptyPoolTip(5, 0), 'two-level tips differ');

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
