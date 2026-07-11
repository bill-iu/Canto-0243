import {
  RESULT_RENDER_BATCH,
  clampVisibleCount,
  resetVisibleCount,
} from '../src/infinite-results-logic.ts';

if (clampVisibleCount(RESULT_RENDER_BATCH, 800) !== RESULT_RENDER_BATCH) {
  throw new Error('infinite-results: load-more must preserve expanded window');
}
if (clampVisibleCount(800, 300) !== 300) {
  throw new Error('infinite-results: shrink must clamp window');
}
if (resetVisibleCount() !== RESULT_RENDER_BATCH) {
  throw new Error('infinite-results: new reset must restore first batch');
}

console.log('infinite-results self-check ok');
