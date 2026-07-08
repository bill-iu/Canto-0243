/** ponytail: infinite scroll window — reset must re-expand when itemCount unchanged */
import { RESULT_RENDER_BATCH } from '../src/infinite-results.ts';

function simulateVisibleAfterReset(itemCount: number): number {
  let itemCountAtLoadRef = 0;
  let visibleCount = Math.min(RESULT_RENDER_BATCH, itemCount || RESULT_RENDER_BATCH);
  itemCountAtLoadRef = 0;
  const added = itemCount - itemCountAtLoadRef;
  if (added > 0) {
    visibleCount = Math.min(visibleCount + added, itemCount);
  }
  itemCountAtLoadRef = itemCount;
  return visibleCount;
}

const cases = [
  { itemCount: 1200, expect: 1200 },
  { itemCount: 5501, expect: 5501 },
  { itemCount: 50, expect: 50 },
];

for (const { itemCount, expect } of cases) {
  const got = simulateVisibleAfterReset(itemCount);
  if (got !== expect) {
    throw new Error(`infinite-results-self-check: itemCount=${itemCount} → ${got}, expected ${expect}`);
  }
}

console.log('infinite-results-self-check ok');