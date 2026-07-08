import { useCallback, useEffect, useRef, useState } from 'react';
import { isSentinelIntersecting } from '../../frontend/infinite-results.mjs';

export const RESULT_RENDER_BATCH = 200;
const SCROLL_MARGIN = 200;

type UseInfiniteResultWindowOptions = {
  itemCount: number;
  hasMore: boolean;
  loading: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  resetKey: string;
  scrollRoot?: Element | null;
};

export function useInfiniteResultWindow({
  itemCount,
  hasMore,
  loading,
  loadingMore,
  onLoadMore,
  resetKey,
  scrollRoot = null,
}: UseInfiniteResultWindowOptions) {
  const [visibleCount, setVisibleCount] = useState(RESULT_RENDER_BATCH);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const cooldownRef = useRef(false);

  useEffect(() => {
    setVisibleCount(Math.min(RESULT_RENDER_BATCH, itemCount || RESULT_RENDER_BATCH));
  }, [resetKey]);

  const onNeedMore = useCallback(() => {
    if (loading || loadingMore || cooldownRef.current) return;
    cooldownRef.current = true;
    requestAnimationFrame(() => {
      cooldownRef.current = false;
    });
    setVisibleCount((prev) => {
      if (prev < itemCount) {
        return Math.min(prev + RESULT_RENDER_BATCH, itemCount);
      }
      if (hasMore) onLoadMore();
      return prev;
    });
  }, [itemCount, hasMore, loading, loadingMore, onLoadMore]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    const root = scrollRoot;
    if (!sentinel || !root || itemCount === 0) return;
    const maybeLoad = () => {
      if (!isSentinelIntersecting(root, sentinel, SCROLL_MARGIN)) return;
      onNeedMore();
    };
    root.addEventListener('scroll', maybeLoad, { passive: true });
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) maybeLoad();
      },
      { root, rootMargin: `${SCROLL_MARGIN}px`, threshold: 0 },
    );
    observer.observe(sentinel);
    return () => {
      root.removeEventListener('scroll', maybeLoad);
      observer.disconnect();
    };
  }, [itemCount, onNeedMore, scrollRoot]);

  const canExpand = visibleCount < itemCount;
  const showSentinel = itemCount > 0 && (canExpand || hasMore);

  return {
    sentinelRef,
    visibleCount: Math.min(visibleCount, itemCount),
    showSentinel,
  };
}