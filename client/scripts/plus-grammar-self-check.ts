import { maskFromCanonicalPlusQuery } from '../src/db/plus-grammar.ts';
import { normalizeAndParse } from '../src/db/query-engine.ts';
import { QueryKind } from '../src/db/query-kind.ts';

const cases: Array<[string, string | null]> = [
  ['+香??', '香??'],
  ['?+你?', '?你?'],
  ['+門0', '門0'],
  ['23+好', null],
];

for (const [q, expected] of cases) {
  const got = maskFromCanonicalPlusQuery(q);
  if (got !== expected) {
    throw new Error(`maskFromCanonicalPlusQuery(${q}) = ${got}, want ${expected}`);
  }
}

for (const q of ['+香??', '?+你?']) {
  const parsed = normalizeAndParse(q);
  if (parsed.kind !== QueryKind.MASK) {
    throw new Error(`normalizeAndParse(${q}) kind=${parsed.kind}, want mask`);
  }
}

console.log('plus-grammar-self-check: ok');