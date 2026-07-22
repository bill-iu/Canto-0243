/** ADR-0062: initial `^` normalize + parity with legacy left `=`. */
import { normalizeAndParse } from '../src/db/query/parse.ts';
import { normalizeQuery } from '../src/db/query/grammar/normalize.ts';
import { buildEqualsMatchSpec } from '../src/db/query/grammar/equals.ts';
import { getEqualsSpan } from '../src/db/position-match/spec.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';
import { QueryKind } from '../src/db/query-kind.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`initial-caret-syntax: ${message}`);
}

function slotKey(q: string): string {
  const parsed = normalizeAndParse(q, { mode: 'm1' });
  const spec = buildMatchSpecForParsed(parsed);
  assert(spec, `no spec for ${q}`);
  const slots = (spec.slots ?? []).map((s) => `${s.pos}:${s.kind}:${s.value}`).join('|');
  const span = getEqualsSpan(spec);
  const spanKey = span ? `${span.dimension}:${span.ref_literal}:${span.start_pos}` : '';
  return `${spec.width};${slots};${spanKey}`;
}

assert(normalizeQuery('=就') === '^就', 'normalize =就');
assert(normalizeQuery('?=就') === '?^就', 'normalize ?=就');
assert(normalizeQuery('2=我3') === '2^我3', 'normalize 2=我3');
assert(normalizeQuery('04=困49=倒') === '04^困49^倒', 'normalize serial initial');
assert(normalizeQuery('就=') === '就=', 'preserve rhyme');
assert(normalizeQuery('23就') === '23就=', 'sandwich still appends =');

for (const [oldQ, newQ] of [
  ['=就', '^就'],
  ['?=就', '?^就'],
  ['2=我3', '2^我3'],
  ['04=困49=倒', '04^困49^倒'],
  ['=香港', '^香港'],
] as const) {
  assert(slotKey(oldQ) === slotKey(newQ), `parity ${oldQ} ≡ ${newQ}`);
}

const caret = buildEqualsMatchSpec('2^我3');
const legacy = buildEqualsMatchSpec('2=我3');
assert(caret && legacy, 'framed specs');
assert(getEqualsSpan(caret!)?.dimension === 'initial', 'caret initial');
assert(getEqualsSpan(legacy!)?.dimension === 'initial', 'legacy initial');

for (const q of ['^香=', '^香港=', '04困=49^倒'] as const) {
  const parsed = normalizeAndParse(q, { mode: 'm1' });
  assert(parsed.kind === QueryKind.UNMATCHED, `dual mark reject ${q}`);
  assert(typeof (parsed as { hint?: string }).hint === 'string', `hint ${q}`);
}

assert(normalizeAndParse('香港', { mode: 'm1' }).kind === QueryKind.WORD_LOOKUP, 'literal lookup');

console.log('initial-caret-syntax self-check ok');
