/**
 * React Hook for Database Management
 * Provides easy access to the SQL.js database in React components
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useLayoutEffect,
  useCallback,
  type ReactNode,
} from 'react';
import {
  initializeDatabase,
  getDefaultDbUrl,
  isDatabaseInitialized,
  isLexiconCachedForBackend,
  resetDatabase,
} from '../db/init';
import {
  search,
  searchPage,
  getDatabaseStats,
  validateOfflineReadiness,
  normalizeQuery,
  parseQuery,
  normalizeAndParse,
  SEARCH_PAGE_SIZE,
} from '../db/query';
import type {
  QueryOptions,
  QueryResult,
  QueryMode,
  QueryKind,
  SearchPageResult,
} from '../db/query';

// Re-export query engine types and functions for convenience
export type { QueryMode, QueryKind, QueryOptions, QueryResult, SearchPageResult };
export { normalizeQuery, parseQuery, normalizeAndParse, SEARCH_PAGE_SIZE };

/**
 * Database status type
 */
export type DatabaseStatus = 'idle' | 'loading' | 'ready' | 'error';

export type OfflineReadinessStatus = 'not_ready' | 'preparing' | 'ready' | 'failed';

/**
 * Database hook return type
 */
export interface UseDBReturn {
  status: DatabaseStatus;
  offlineStatus: OfflineReadinessStatus;
  isOfflineReady: boolean;
  isOnline: boolean;
  isDbCached: boolean | null;
  dbUrl: string;
  progress: number;
  error: Error | null;
  isReady: boolean;
  initialize: () => Promise<void>;
  retryOfflineReady: () => Promise<void>;
  search: (options: QueryOptions) => Promise<QueryResult[]>;
  getStats: () => Promise<{ wordCount: number; tableCount: number }>;
  reset: () => void;
}

const DBContext = createContext<UseDBReturn | null>(null);

function useDBState(): UseDBReturn {
  const [status, setStatus] = useState<DatabaseStatus>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [isDbCached, setIsDbCached] = useState<boolean | null>(null);
  const [isValidated, setIsValidated] = useState<boolean>(false);

  const dbUrl = getDefaultDbUrl();

  const checkDbCached = useCallback(async () => {
    try {
      setIsDbCached(await isLexiconCachedForBackend());
    } catch {
      setIsDbCached(false);
    }
  }, []);

  const initialize = useCallback(async () => {
    if (status === 'loading') {
      return;
    }
    if (status === 'ready' && isValidated) {
      return;
    }

    try {
      setStatus('loading');
      setError(null);
      setProgress(0);
      setIsValidated(false);

      await initializeDatabase();
      await validateOfflineReadiness();
      setIsValidated(true);

      setStatus('ready');
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      setStatus('error');
      setProgress(0);
      setIsValidated(false);
    }
  }, [status, isValidated]);

  const retryOfflineReady = useCallback(async () => {
    resetDatabase();
    setStatus('idle');
    setProgress(0);
    setError(null);
    setIsValidated(false);
    await checkDbCached();
    await initialize();
  }, [checkDbCached, initialize]);

  const searchQuery = useCallback(async (options: QueryOptions) => {
    if (!isDatabaseInitialized()) {
      await initialize();
    }
    if (!isDatabaseInitialized()) {
      throw new Error('Database not ready');
    }
    return search(options);
  }, [initialize]);

  const getStats = useCallback(async () => {
    if (!isDatabaseInitialized()) {
      await initialize();
    }
    if (!isDatabaseInitialized()) {
      throw new Error('Database not ready');
    }
    return getDatabaseStats();
  }, [initialize]);

  const reset = useCallback(() => {
    resetDatabase();
    setStatus('idle');
    setProgress(0);
    setError(null);
    setIsValidated(false);
  }, []);

  useEffect(() => {
    if (!isDatabaseInitialized() || status !== 'idle') {
      return;
    }
    void (async () => {
      try {
        await validateOfflineReadiness();
        setIsValidated(true);
        setStatus('ready');
        setProgress(100);
      } catch {
        // ponytail: let App auto-initialize on online/cache
      }
    })();
  }, [status]);

  useEffect(() => {
    checkDbCached();
  }, [checkDbCached]);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  const offlineStatus: OfflineReadinessStatus =
    status === 'ready' && isValidated
      ? 'ready'
      : status === 'loading'
        ? 'preparing'
        : status === 'error'
          ? 'failed'
          : 'not_ready';

  return {
    status,
    offlineStatus,
    isOfflineReady: offlineStatus === 'ready',
    isOnline,
    isDbCached,
    dbUrl,
    progress,
    error,
    isReady: offlineStatus === 'ready',
    initialize,
    retryOfflineReady,
    search: searchQuery,
    getStats,
    reset,
  };
}

export function DBProvider({ children }: { children: ReactNode }) {
  const value = useDBState();
  return <DBContext.Provider value={value}>{children}</DBContext.Provider>;
}

/**
 * Custom hook for managing the SQL.js database (shared via DBProvider)
 */
export function useDB(): UseDBReturn {
  const ctx = useContext(DBContext);
  if (!ctx) {
    throw new Error('useDB must be used within DBProvider');
  }
  return ctx;
}

/**
 * Hook for a specific query with loading state and load-more pagination.
 */
export function useSearch(
  query: string,
  mode: QueryOptions['mode'] = '0243',
  options?: { pageSize?: number; fallback_0243_mode?: '0243' | '02493' },
) {
  const pageSize = options?.pageSize ?? SEARCH_PAGE_SIZE;
  const fallback0243Mode = options?.fallback_0243_mode;
  const { isReady, status } = useDB();
  const [results, setResults] = useState<QueryResult[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<Error | null>(null);
  const [lastPageSize, setLastPageSize] = useState(0);

  const trimmed = query.trim();
  const canSearch = Boolean(trimmed) && isReady;

  const hasMore =
    canSearch &&
    ((total != null && results.length < total) ||
      (total == null && lastPageSize >= pageSize));

  useLayoutEffect(() => {
    if (!canSearch) {
      setResults([]);
      setTotal(null);
      setHint(null);
      setLoading(false);
      setLastPageSize(0);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setSearchError(null);

    const run = async () => {
      try {
        const page = await searchPage({
          query: trimmed,
          mode,
          limit: pageSize,
          offset: 0,
          fallback_0243_mode: fallback0243Mode,
        });
        if (!cancelled) {
          setResults(page.items);
          setTotal(page.total ?? null);
          setHint(page.hint ?? null);
          setLastPageSize(page.items.length);
        }
      } catch (err) {
        if (!cancelled) {
          setSearchError(err instanceof Error ? err : new Error(String(err)));
          setResults([]);
          setTotal(null);
          setHint(null);
          setLastPageSize(0);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [trimmed, mode, pageSize, canSearch, fallback0243Mode]);

  const loadMore = useCallback(async () => {
    if (!canSearch || loading || loadingMore || !hasMore) {
      return;
    }
    setLoadingMore(true);
    setSearchError(null);
    try {
      const page = await searchPage({
        query: trimmed,
        mode,
        limit: pageSize,
        offset: results.length,
        fallback_0243_mode: fallback0243Mode,
      });
      setResults((prev) => [...prev, ...page.items]);
      if (page.total != null) {
        setTotal(page.total);
      }
      setLastPageSize(page.items.length);
    } catch (err) {
      setSearchError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoadingMore(false);
    }
  }, [canSearch, loading, loadingMore, hasMore, trimmed, mode, pageSize, results.length, fallback0243Mode]);

  return {
    results,
    total,
    hint,
    loading: loading || status === 'loading',
    loadingMore,
    error: searchError,
    isReady,
    hasMore,
    loadMore,
  };
}

export default useDB;
