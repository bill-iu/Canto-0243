/** ponytail: shared infinite-scroll batch size (0243.hk uses +50 per scroll). */
export const RESULT_RENDER_BATCH = 50;
export const SCROLL_ROOT_MARGIN = "200px";

export function wireInfiniteScroll({ root, sentinel, onNeedMore }) {
  if (!sentinel || !onNeedMore) return () => {};
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) onNeedMore();
    },
    { root: root || null, rootMargin: SCROLL_ROOT_MARGIN, threshold: 0 },
  );
  observer.observe(sentinel);
  return () => observer.disconnect();
}

export function effectiveRenderedCount(tab, itemCount, batch = RESULT_RENDER_BATCH) {
  const raw = tab?.renderedCount ?? batch;
  return Math.min(raw, itemCount);
}

export function canExpandRenderedCount(tab, itemCount) {
  return effectiveRenderedCount(tab, itemCount) < itemCount;
}

export function expandRenderedCount(tab, itemCount, batch = RESULT_RENDER_BATCH) {
  const next = Math.min((tab.renderedCount ?? batch) + batch, itemCount);
  tab.renderedCount = next;
  return next;
}

export function resetRenderedCount(tab, itemCount, batch = RESULT_RENDER_BATCH) {
  tab.renderedCount = Math.min(batch, itemCount);
}