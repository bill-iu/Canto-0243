import { parseManualCell, parseSpanManual } from '../src/workbench/manual-slot-input.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`manual slot: ${message}`);
}

const han = parseManualCell('香');
assert(han.ok && han.surface === '香', 'hanzi');
const digit = parseManualCell('4');
assert(digit.ok && digit.code === '4' && digit.surface === '', 'digit');
assert(!parseManualCell('').ok, 'empty');
assert(!parseManualCell('??').ok && !parseManualCell('?').ok, 'wildcard cell');
assert(!parseManualCell('香港').ok, 'two chars');
assert(!parseManualCell('a').ok, 'latin');

const span = parseSpanManual('香江', 2);
assert(span.ok && span.slots.length === 2, 'span surface');
assert(!parseSpanManual('香', 2).ok, 'width mismatch');
assert(!parseSpanManual('??', 2).ok, 'wildcard span');
assert(parseSpanManual('44', 2).ok, 'span code');
assert(parseSpanManual('能4', 2).ok, 'span mixed');

console.log('manual slot self-check ok');
