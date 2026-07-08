import { useCallback, useEffect, useRef, useState } from 'react';
import { isSentinelIntersecting } from '../../frontend/infinite-results.mjs';

export const RESULT_RENDER_BATCH = 50;
const SCROLL_ROOT_MARGIN = '200px';

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
  const armedRef = useRef(true);

  useEffect(() => {
    setVisibleCount(Math.min(RESULT_RENDER_BATCH, itemCount || RESULT_RENDER_BATCH));
  }, [resetKey]);

  const onNeedMore = useCallback(() => {
    if (loading || loadingMore || !armedRef.current) return;
    armedRef.current = false;
    requestAnimationFrame(() => {
      armedRef.current = true;
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
    if (!sentinel || itemCount === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) onNeedMore();
      },
      { root: scrollRoot, rootMargin: SCROLL_ROOT_MARGIN, threshold: 0 },
    );
    observer.observe(sentinel);
    const onScroll = () => {
      if (isSentinelIntersecting(scrollRoot, sentinel, 0)) onNeedMore();
    };
    scrollRoot?.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      observer.disconnect();
      scrollRoot?.removeEventListener('scroll', onScroll);
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