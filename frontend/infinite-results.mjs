/** ponytail: shared infinite-scroll batch size (0243.hk uses +50 per scroll). */
export const RESULT_RENDER_BATCH = 50;
export const SCROLL_ROOT_MARGIN = "200px";

const nextFrame =
  typeof requestAnimationFrame === "function"
    ? requestAnimationFrame
    : (fn) => setTimeout(fn, 16);

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

/** One expand/fetch per frame; scroll listener backs up IO when sentinel stays visible. */
export function wireInfiniteScroll({ root, sentinel, onNeedMore }) {
  if (!sentinel || !onNeedMore) return () => {};
  let armed = true;
  const trigger = () => {
    if (!armed) return;
    armed = false;
    onNeedMore();
    nextFrame(() => {
      armed = true;
    });
  };
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) trigger();
    },
    { root: root || null, rootMargin: SCROLL_ROOT_MARGIN, threshold: 0 },
  );
  observer.observe(sentinel);
  const onScroll = () => {
    if (isSentinelIntersecting(root, sentinel, 0)) trigger();
  };
  root?.addEventListener("scroll", onScroll, { passive: true });
  return () => {
    observer.disconnect();
    root?.removeEventListener("scroll", onScroll);
  };
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