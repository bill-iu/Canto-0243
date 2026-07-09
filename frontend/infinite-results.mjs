/** ponytail: shared infinite-scroll batch size — 200 chips per scroll step */
export const RESULT_RENDER_BATCH = 400;
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

/** Scroll-root + IO; one batch per frame (no pump). */
export function wireInfiniteScroll({ root, sentinel, onNeedMore }) {
  if (!sentinel || !onNeedMore) return () => {};
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
  const cleanups = [];
  if (root) {
    root.addEventListener("scroll", maybeLoad, { passive: true });
    cleanups.push(() => root.removeEventListener("scroll", maybeLoad));
  }
  if (root && typeof IntersectionObserver !== "undefined") {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) maybeLoad();
      },
      { root, rootMargin: SCROLL_ROOT_MARGIN, threshold: 0 },
    );
    observer.observe(sentinel);
    cleanups.push(() => observer.disconnect());
  }
  return () => cleanups.forEach((fn) => fn());
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