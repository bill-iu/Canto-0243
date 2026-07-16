export const RESULT_RENDER_BATCH = 400;

export function resetVisibleCount(): number {
  return RESULT_RENDER_BATCH;
}

export function clampVisibleCount(visibleCount: number, itemCount: number): number {
  return itemCount > 0 ? Math.min(visibleCount, itemCount) : visibleCount;
}

/**
 * After load-more grows the fetched window: if we were already showing the full
 * previous window, reveal one more 呈現批次 so the list height grows and the
 * user can scroll again (otherwise sentinel stays glued to the viewport edge
 * with no further scroll/IO events — stuck at first-page 400).
 */
export function visibleCountAfterItemsGrow(
  visibleCount: number,
  prevItemCount: number,
  itemCount: number,
  batch: number = RESULT_RENDER_BATCH,
): number {
  if (itemCount <= 0) return visibleCount;
  if (prevItemCount > 0 && visibleCount >= prevItemCount && itemCount > prevItemCount) {
    return Math.min(visibleCount + batch, itemCount);
  }
  return Math.min(visibleCount, itemCount);
}
