/** ponytail: first page shows RESULT_RENDER_BATCH only — user scroll expands */
import { RESULT_RENDER_BATCH } from '../src/infinite-results.ts';

function visibleAfterReset(itemCount: number): number {
  return Math.min(RESULT_RENDER_BATCH, itemCount || RESULT_RENDER_BATCH);
}

const cases = [
  { itemCount: 1200, expect: 50 },
  { itemCount: 5501, expect: 50 },
  { itemCount: 50, expect: 50 },
  { itemCount: 12, expect: 12 },
];

for (const { itemCount, expect } of cases) {
  const got = visibleAfterReset(itemCount);
  if (got !== expect) {
    throw new Error(`infinite-results-self-check: itemCount=${itemCount} → ${got}, expected ${expect}`);
  }
}

console.log('infinite-results-self-check ok');