import {
  buildCodeDigitSlots,
  codeConstraintAfterRemoveCode,
  padExplicitCode,
  planHasQueryableSlots,
  sameToneCodePattern,
  sanitizeExplicitCode,
} from '../src/workbench/code-constraint.ts';
import type { LineSlot } from '../src/workbench/line-draft.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`code-constraint: ${message}`);
}

const slots: LineSlot[] = [
  { surface: '', code: '0', locked: true },
  { surface: '', code: '2', locked: false },
  { surface: '', code: '3', locked: false },
  { surface: '', code: '4', locked: true },
];
const span = { start: 0, width: 4 };

assert(sameToneCodePattern(slots, span) === '0??4', 'jump-lock pattern');
assert(
  buildCodeDigitSlots('same_tone', slots, span, '').map((s) => `${s.pos}${s.digit}`).join(',') === '00,34',
  'same_tone only locked digits',
);
assert(buildCodeDigitSlots('off', slots, span, '0234').length === 0, 'off drops codes');
assert(
  buildCodeDigitSlots('explicit', slots, span, '0?34').map((s) => `${s.pos}${s.digit}`).join(',') === '00,23,34',
  'explicit honors ?',
);
assert(sanitizeExplicitCode('0a?3x', 4) === '0?3', 'sanitize clips');
assert(padExplicitCode('0?', 4) === '0???', 'pad fills');
assert(planHasQueryableSlots([], '稻草', 'ranked'), 'semantic-only queryable');
assert(!planHasQueryableSlots([], '', 'off'), 'bare width not queryable');
assert(planHasQueryableSlots([{ pos: 0, kind: 'code_digit', digit: '2' }], '', 'off'), 'code queryable');

assert(codeConstraintAfterRemoveCode([], 4).mode === 'off', 'no codes → off');
assert(
  codeConstraintAfterRemoveCode(
    [{ pos: 1, kind: 'code_digit', digit: '4' }, { pos: 3, kind: 'code_digit', digit: '9' }],
    4,
  ).explicit === '?4?9',
  'remaining codes → explicit pattern',
);
{
  const next = codeConstraintAfterRemoveCode(
    [{ pos: 0, kind: 'final_anchor', ref: '困' }],
    4,
  );
  assert(next.mode === 'off' && next.explicit === '', 'anchors only → off');
  const rebuilt = buildCodeDigitSlots(next.mode, slots, span, next.explicit);
  assert(rebuilt.length === 0, 'apply remove_code must not re-inject same_tone codes');
}

console.log('code-constraint self-check ok');
