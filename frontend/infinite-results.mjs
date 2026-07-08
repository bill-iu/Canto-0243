/** ponytail: shared infinite-scroll batch size — 200 chips per user scroll step */
export const RESULT_RENDER_BATCH = 200;
export const SCROLL_ROOT_MARGIN = "200px";

const nextFrame =
  typeof requestAnimationFrame === "function"
    ? requestAnimationFrame
    : (fn) => setTimeout(fn, 16);

const marginPx = Number.parseInt(SCROLL_ROOT_MARGIN, 10) || 200;

export function isSentinelIntersecting(root, sentinel, margin = marginPx) {
  if (!sentinel || sentinel.hidden) return false;
  const rect = sentinel.getBoundingClientRect();
  const rootRect = root
    ? root.getBoundingClientRect()
    : { top: 0, left: 0, right: globalThis.innerWidth, bottom: globalThis.innerHeight };
  return rect.top <= rootRect.bottom + margin && rect.bottom >= rootRect.top - margin;
}

/** Scroll-root only — one batch per scroll step; no IO (avoids pre-scroll auto chain). */
export function wireInfiniteScroll({ root, sentinel, onNeedMore }) {
  if (!sentinel || !onNeedMore || !root) return () => {};
  let cooldown = false;
  const maybeLoad = () => {
    if (cooldown || sentinel.hidden) return;
    if (!isSentinelIntersecting(root, sentinel)) return;
    cooldown = true;
    onNeedMore();
    nextFrame(() => {
      cooldown = false;
    });
  };
  root.addEventListener("scroll", maybeLoad, { passive: true });
  return () => root.removeEventListener("scroll", maybeLoad);
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