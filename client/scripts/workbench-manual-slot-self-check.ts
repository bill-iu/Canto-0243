import { parseLineInput } from '../src/workbench/line-input.ts';
import { parseManualCell, parsePhonemeRef, parseSpanManual } from '../src/workbench/manual-slot-input.ts';
import {
  buildPhonemeAnchors,
  emptyPhonemeDimPicks,
  phonemeCheckedOffsets,
} from '../src/workbench/replacement-span.ts';
import { createLineDraft, lineDraftReducer } from '../src/workbench/line-draft.ts';
import { toggleLockKeepingSpan } from '../src/workbench/replacement-span.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`manual slot: ${message}`);
}

const han = parseManualCell('香');
assert(han.ok && han.surface === '香', 'hanzi');
const digit = parseManualCell('4');
assert(digit.ok && digit.code === '4' && digit.surface === '', 'digit');
assert(!parseManualCell('').ok, 'empty');
assert(parseManualCell('?').ok && (parseManualCell('?') as { surface: string }).surface === '?', 'wildcard ?');
assert(parseManualCell('_').ok && (parseManualCell('_') as { surface: string }).surface === '?', 'wildcard _');
assert(!parseManualCell('香港').ok, 'two chars');
assert(!parseManualCell('a').ok, 'latin');

const span = parseSpanManual('香江', 2);
assert(span.ok && span.slots.length === 2, 'span surface');
assert(!parseSpanManual('香', 2).ok, 'width mismatch');
assert(parseSpanManual('??', 2).ok, 'wildcard span');
assert(parseSpanManual('44', 2).ok, 'span code');
assert(parseSpanManual('能4', 2).ok, 'span mixed');

const line = parseLineInput('?香??');
assert(line.ok && line.slots.map((s) => s.surface).join('') === '?香??', 'line wildcards');

assert(parsePhonemeRef('', 2).ok && (parsePhonemeRef('', 2) as { chars: null }).chars === null, 'empty ref');
assert(parsePhonemeRef('困', 1).ok, 'one-char ref for one check');
assert(!parsePhonemeRef('困潦', 1).ok, 'too many for one check');
assert(parsePhonemeRef('困潦倒', 3).ok, 'whole span ref');
assert(!parsePhonemeRef('困潦', 3).ok, 'short whole ref');
assert(parsePhonemeRef('香?港', 3).ok, 'mixed ? in ref');

{
  const parsed = parseLineInput('香港人');
  assert(parsed.ok, 'seed line');
  let draft = createLineDraft(parsed);
  let lock = toggleLockKeepingSpan(draft, 0);
  assert(lock.ok, 'lock0');
  draft = lock.draft;
  lock = toggleLockKeepingSpan(draft, 1);
  assert(lock.ok, 'lock1');
  draft = lock.draft;
  lock = toggleLockKeepingSpan(draft, 2);
  assert(lock.ok, 'lock2');
  draft = lock.draft;
  draft = lineDraftReducer(draft, { type: 'choose_reading', pos: 1, jyutping: 'gong2', code: '3' });
  const picks = { whole: false, head: false, tail: false, middles: [1] };
  assert(phonemeCheckedOffsets(picks, 3).length === 1, 'one checked');
  const readings = new Map([['江', 'gong2']]);
  const anchors = buildPhonemeAnchors(
    draft.selection!,
    draft.slots,
    picks,
    emptyPhonemeDimPicks(),
    ['江'],
    null,
    readings,
  );
  assert(anchors.length === 1 && anchors[0]?.ref === '江', 'override ref');
}

{
  const parsed = parseLineInput('????');
  assert(parsed.ok, 'all wild');
  let draft = createLineDraft(parsed);
  let lock = toggleLockKeepingSpan(draft, 0);
  assert(lock.ok, 'wild lock');
  draft = lock.draft;
  assert(draft.slots[0]?.locked && draft.selection?.width === 1, 'wild span');
}

console.log('manual slot self-check ok');
