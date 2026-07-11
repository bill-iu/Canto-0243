export const RESULT_RENDER_BATCH = 400;

export function resetVisibleCount(): number {
  return RESULT_RENDER_BATCH;
}

export function clampVisibleCount(visibleCount: number, itemCount: number): number {
  return itemCount > 0 ? Math.min(visibleCount, itemCount) : visibleCount;
}
