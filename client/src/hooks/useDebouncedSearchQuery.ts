import { useCallback, useEffect, useRef, useState } from 'react';

const DEBOUNCE_MS = 300;

/**
 * 輸入即時更新 inputQuery；searchQuery debounce 或 flush 立即更新（供 useSearch）。
 */
export function useDebouncedSearchQuery(initialQuery = '') {
  const [inputQuery, setInputQuery] = useState(initialQuery);
  const [searchQuery, setSearchQuery] = useState(initialQuery.trim());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const scheduleSearchQuery = useCallback((next: string) => {
    clearTimer();
    timerRef.current = setTimeout(() => {
      setSearchQuery(next.trim());
      timerRef.current = null;
    }, DEBOUNCE_MS);
  }, []);

  const setInputQueryDebounced = useCallback(
    (next: string) => {
      setInputQuery(next);
      scheduleSearchQuery(next);
    },
    [scheduleSearchQuery],
  );

  const flushSearchQuery = useCallback((next?: string) => {
    clearTimer();
    const value = (next ?? inputQuery).trim();
    setSearchQuery(value);
    if (next !== undefined) {
      setInputQuery(next);
    }
  }, [inputQuery]);

  const hydrateSearch = useCallback((q: string) => {
    clearTimer();
    setInputQuery(q);
    setSearchQuery(q.trim());
  }, []);

  useEffect(() => () => clearTimer(), []);

  return {
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    flushSearchQuery,
    hydrateSearch,
  };
}
