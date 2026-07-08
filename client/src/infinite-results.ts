import { useCallback, useEffect, useRef, useState } from 'react';

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
  const itemCountAtLoadRef = useRef(0);

  useEffect(() => {
    itemCountAtLoadRef.current = 0;
    setVisibleCount(Math.min(RESULT_RENDER_BATCH, itemCount || RESULT_RENDER_BATCH));
  }, [resetKey]);

  useEffect(() => {
    if (loadingMore) {
      itemCountAtLoadRef.current = itemCount;
      return;
    }
    const added = itemCount - itemCountAtLoadRef.current;
    if (added > 0) {
      setVisibleCount((prev) => Math.min(prev + added, itemCount));
    }
    itemCountAtLoadRef.current = itemCount;
  }, [loadingMore, itemCount]);

  const onNeedMore = useCallback(() => {
    if (loading || loadingMore) return;
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
    return () => observer.disconnect();
  }, [itemCount, onNeedMore, scrollRoot]);

  const canExpand = visibleCount < itemCount;
  const showSentinel = itemCount > 0 && (canExpand || hasMore);

  return {
    sentinelRef,
    visibleCount: Math.min(visibleCount, itemCount),
    showSentinel,
  };
}