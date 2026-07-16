import {
  RESULT_RENDER_BATCH,
  clampVisibleCount,
  resetVisibleCount,
  visibleCountAfterItemsGrow,
} from '../src/infinite-results-logic.ts';

if (clampVisibleCount(RESULT_RENDER_BATCH, 800) !== RESULT_RENDER_BATCH) {
  throw new Error('infinite-results: clamp must not jump ahead of painted window');
}
if (clampVisibleCount(800, 300) !== 300) {
  throw new Error('infinite-results: shrink must clamp window');
}
if (resetVisibleCount() !== RESULT_RENDER_BATCH) {
  throw new Error('infinite-results: new reset must restore first batch');
}

// Red→green: first page 400, load-more grows fetched set, paint next batch
const afterFirstPage = visibleCountAfterItemsGrow(400, 0, 400);
if (afterFirstPage !== 400) {
  throw new Error(`infinite-results: first page paint → ${afterFirstPage}`);
}
const afterLoadMore = visibleCountAfterItemsGrow(400, 400, 1200);
if (afterLoadMore !== 800) {
  throw new Error(
    `infinite-results: after load-more must expand one batch (got ${afterLoadMore})`,
  );
}
const afterSecondScrollPaint = visibleCountAfterItemsGrow(800, 1200, 1200);
if (afterSecondScrollPaint !== 800) {
  throw new Error(`infinite-results: no extra expand without growth → ${afterSecondScrollPaint}`);
}
const afterSecondLoadMore = visibleCountAfterItemsGrow(1200, 1200, 2000);
if (afterSecondLoadMore !== 1600) {
  throw new Error(`infinite-results: caught-up grow → ${afterSecondLoadMore}`);
}

console.log('infinite-results self-check ok');
