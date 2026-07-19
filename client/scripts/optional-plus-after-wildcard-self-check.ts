/** A1: ?錨 ≡ ?+錨 widths; bare anchor stays 1-slot. */
import { normalizeAndParse } from '../src/db/query/parse.ts';
import { normalizeQuery } from '../src/db/query/grammar/normalize.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`optional-plus-after-wildcard: ${message}`);
}

function width(q: string): number {
  const parsed = normalizeAndParse(q, { mode: 'm1' });
  const spec = buildMatchSpecForParsed(parsed);
  assert(spec, `no spec for ${q}`);
  return spec.width;
}

assert(normalizeQuery('?就=') === '?就=', 'PWA must not strip leading ? on rhyme');
assert(width('?就=') === 2 && width('?+就=') === 2, '?就= ≡ ?+就=');
assert(width('就=') === 1, '就= stays one slot');
assert(normalizeQuery('?=就') === '?^就', 'legacy left = → ^');
assert(width('?=就') === 2 && width('?+=就') === 2 && width('?^就') === 2, '?=就 ≡ ?^就');
assert(width('=就') === 1 && width('^就') === 1, '^就 stays one slot');
assert(width('?hon') === 2 && width('?+hon') === 2, '?hon ≡ ?+hon');

console.log('optional-plus-after-wildcard self-check ok');
