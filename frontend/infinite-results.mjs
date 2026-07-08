/** ponytail: shared infinite-scroll batch size (0243.hk uses +50 per scroll). */
export const RESULT_RENDER_BATCH = 50;
export const SCROLL_ROOT_MARGIN = "200px";
export const SCROLL_PUMP_MAX_STEPS = 8;

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

/** IO fires once per enter; pump while sentinel stays in the scroll root. */
export function isSentinelIntersecting(root, sentinel, marginPx = 200) {
  if (!sentinel || sentinel.hidden) return false;
  const rect = sentinel.getBoundingClientRect();
  const rootRect = root
    ? root.getBoundingClientRect()
    : { top: 0, left: 0, right: globalThis.innerWidth, bottom: globalThis.innerHeight };
  return (
    rect.top <= rootRect.bottom + marginPx && rect.bottom >= rootRect.top - marginPx
  );
}

const nextFrame =
  typeof requestAnimationFrame === "function"
    ? requestAnimationFrame
    : (fn) => setTimeout(fn, 16);

export function scheduleScrollPump({ root, sentinel, onStep, maxSteps = SCROLL_PUMP_MAX_STEPS }) {
  if (!sentinel || !onStep) return;
  let steps = 0;
  const tick = () => {
    if (steps >= maxSteps || !isSentinelIntersecting(root, sentinel)) return;
    onStep();
    steps += 1;
    if (isSentinelIntersecting(root, sentinel)) nextFrame(tick);
  };
  nextFrame(tick);
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

/** Show every row already fetched for this tab (up to SEARCH_PAGE_SIZE). */
export function revealFetchedPage(tab, itemCount) {
  tab.renderedCount = itemCount;
  return itemCount;
}