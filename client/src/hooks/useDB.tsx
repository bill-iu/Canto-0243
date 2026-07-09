/**
 * React Hook for Database Management
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useLayoutEffect,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import {
  initializeDatabase,
  getCurrentLexiconTarget,
  getDefaultDbUrl,
  isDatabaseInitialized,
  isLexiconCachedForBackend,
  removeLexiconFromOpfs,
  resetDatabase,
  clearOpfsVfsSessionSkip,
} from '../db/init';
import {
  search,
  searchPage,
  getDatabaseStats,
  validateOfflineReadiness,
  normalizeQuery,
  parseQuery,
  normalizeAndParse,
  searchPageSizeForMode,
  searchLimitForOffset,
  SEARCH_FIRST_PAGE_SIZE,
} from '../db/query';
import type {
  QueryOptions,
  QueryResult,
  QueryMode,
  QueryKind,
  SearchPageResult,
} from '../db/query';
import { isSearchCancelledError } from '../db/search-cancel.ts';
import { reportGatePhase, subscribeGateProgress, resetGateProgressListeners } from '../db/startup-progress.ts';
import {
  getTailProgress,
  isStartupComplete,
  startTailPreload,
  subscribeTailProgress,
  resetTailPreload,
} from '../db/tail-preload.ts';

export type { QueryMode, QueryKind, QueryOptions, QueryResult, SearchPageResult };
export {
  normalizeQuery,
  parseQuery,
  normalizeAndParse,
  SEARCH_PAGE_SIZE,
  SEARCH_FIRST_PAGE_SIZE,
  searchPageSizeForMode,
  searchLimitForOffset,
} from '../db/query.ts';

export type DatabaseStatus = 'idle' | 'loading' | 'ready' | 'error';
export type OfflineReadinessStatus = 'not_ready' | 'preparing' | 'ready' | 'failed';

const WARM_FAST_PATH_MS = 500;

export interface UseDBReturn {
  status: DatabaseStatus;
  offlineStatus: OfflineReadinessStatus;
  isOfflineReady: boolean;
  isOnline: boolean;
  isDbCached: boolean | null;
  dbUrl: string;
  progress: number;
  tailProgress: number;
  startupComplete: boolean;
  suppressGateOverlay: boolean;
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
  const [tailProgress, setTailProgress] = useState<number>(0);
  const [startupComplete, setStartupComplete] = useState<boolean>(false);
  const [suppressGateOverlay, setSuppressGateOverlay] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [isDbCached, setIsDbCached] = useState<boolean | null>(null);
  const [isValidated, setIsValidated] = useState<boolean>(false);
  const initializeInFlightRef = useRef<Promise<void> | null>(null);
  const initStartedAtRef = useRef<number | null>(null);
  const hadCacheAtInitRef = useRef(false);
  const statusRef = useRef(status);
  const isValidatedRef = useRef(isValidated);
  statusRef.current = status;
  isValidatedRef.current = isValidated;

  const dbUrl = getDefaultDbUrl();

  const checkDbCached = useCallback(async () => {
    try {
      setIsDbCached(await isLexiconCachedForBackend());
    } catch {
      setIsDbCached(false);
    }
  }, []);

  useEffect(() => {
    const unsubGate = subscribeGateProgress(setProgress);
    const unsubTail = subscribeTailProgress((p) => {
      setTailProgress(p);
      if (p >= 100) setStartupComplete(true);
    });
    return () => {
      unsubGate();
      unsubTail();
    };
  }, []);

  const initialize = useCallback(async () => {
    if (initializeInFlightRef.current) {
      return initializeInFlightRef.current;
    }
    if (statusRef.current === 'ready' && isValidatedRef.current) {
      return;
    }

    const run = (async () => {
      try {
        setStatus('loading');
        setError(null);
        setProgress(0);
        setIsValidated(false);
        setStartupComplete(false);
        setSuppressGateOverlay(false);
        initStartedAtRef.current = performance.now();
        hadCacheAtInitRef.current = await isLexiconCachedForBackend();

        await initializeDatabase();
        reportGatePhase('validate', 0.3);
        await validateOfflineReadiness();
        reportGatePhase('validate', 1);
        setIsValidated(true);

        const elapsed = performance.now() - (initStartedAtRef.current ?? performance.now());
        if (hadCacheAtInitRef.current && elapsed < WARM_FAST_PATH_MS) {
          setSuppressGateOverlay(true);
        }

        setStatus('ready');
        setProgress(100);
        void startTailPreload();
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
        setStatus('error');
        setProgress(0);
        setIsValidated(false);
      }
    })();

    initializeInFlightRef.current = run;
    try {
      await run;
    } finally {
      if (initializeInFlightRef.current === run) {
        initializeInFlightRef.current = null;
      }
    }
  }, []);

  const retryOfflineReady = useCallback(async () => {
    resetDatabase();
    resetGateProgressListeners();
    resetTailPreload();
    setStatus('idle');
    setProgress(0);
    setTailProgress(0);
    setStartupComplete(false);
    setSuppressGateOverlay(false);
    setError(null);
    setIsValidated(false);
    clearOpfsVfsSessionSkip();
    try {
      const target = await getCurrentLexiconTarget();
      await removeLexiconFromOpfs(target.version);
    } catch {
      /* ponytail: purge stale OPFS best-effort */
    }
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
    resetGateProgressListeners();
    setStatus('idle');
    setProgress(0);
    setTailProgress(0);
    setStartupComplete(false);
    setSuppressGateOverlay(false);
    setError(null);
    setIsValidated(false);
  }, []);

  useEffect(() => {
    if (initializeInFlightRef.current || !isDatabaseInitialized() || status !== 'idle') {
      return;
    }
    void (async () => {
      try {
        reportGatePhase('validate', 0.3);
        await validateOfflineReadiness();
        reportGatePhase('validate', 1);
        setIsValidated(true);
        setStatus('ready');
        setProgress(100);
        void startTailPreload();
      } catch {
        /* ponytail: let App auto-initialize */
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
    tailProgress,
    startupComplete: startupComplete || isStartupComplete(),
    suppressGateOverlay,
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

export function useDB(): UseDBReturn {
  const ctx = useContext(DBContext);
  if (!ctx) {
    throw new Error('useDB must be used within DBProvider');
  }
  return ctx;
}

const SEARCH_LOADING_LABEL_DELAY_MS = 150;

export function useSearch(
  query: string,
  mode: QueryOptions['mode'] = '0243',
  options?: { pageSize?: number; fallback_0243_mode?: '0243' | '02493' | '394052'; ui_lang?: 'zh' | 'en' },
) {
  const fallback0243Mode = options?.fallback_0243_mode;
  const uiLang = options?.ui_lang ?? 'zh';
  const { isReady, status } = useDB();
  const [results, setResults] = useState<QueryResult[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingVisible, setLoadingVisible] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<Error | null>(null);
  const [lastPageSize, setLastPageSize] = useState(0);
  const genRef = useRef(0);

  const trimmed = query.trim();
  const canSearch = Boolean(trimmed) && isReady;
  const firstPageLimit = options?.pageSize ?? searchLimitForOffset(mode, 0);
  const morePageLimit = options?.pageSize ?? searchLimitForOffset(mode, 1);
  // 首屏滿頁或已知 total 未取完 → 可 load-more
  const hasMoreThreshold = mode === 'synonym' ? morePageLimit : SEARCH_FIRST_PAGE_SIZE;

  const hasMore =
    canSearch &&
    ((total != null && results.length < total) ||
      (total == null && lastPageSize >= hasMoreThreshold));

  useLayoutEffect(() => {
    if (!canSearch) {
      genRef.current += 1;
      setResults([]);
      setTotal(null);
      setHint(null);
      setLoading(false);
      setLastPageSize(0);
      return;
    }

    const gen = ++genRef.current;
    const shouldCancel = () => gen !== genRef.current;
    // P3: keep prior results (stale) while loading; do not clear here
    setLoading(true);
    setSearchError(null);

    const run = async () => {
      try {
        const page = await searchPage({
          query: trimmed,
          mode,
          limit: firstPageLimit,
          offset: 0,
          fallback_0243_mode: fallback0243Mode,
          ui_lang: uiLang,
          shouldCancel,
        });
        if (shouldCancel()) return;
        setResults(page.items);
        setTotal(page.total ?? null);
        setHint(page.hint ?? null);
        setLastPageSize(page.items.length);
      } catch (err) {
        if (shouldCancel() || isSearchCancelledError(err)) return;
        setSearchError(err instanceof Error ? err : new Error(String(err)));
        setResults([]);
        setTotal(null);
        setHint(null);
        setLastPageSize(0);
      } finally {
        if (!shouldCancel()) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      genRef.current += 1;
    };
  }, [trimmed, mode, firstPageLimit, canSearch, fallback0243Mode, uiLang]);

  const isLoading = loading || status === 'loading';

  // P3: show "搜尋中" even when stale prior results are still on screen
  useEffect(() => {
    if (!isLoading) {
      setLoadingVisible(false);
      return;
    }
    const timer = window.setTimeout(() => setLoadingVisible(true), SEARCH_LOADING_LABEL_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [isLoading]);

  const loadMore = useCallback(async () => {
    if (!canSearch || loading || loadingMore || !hasMore) {
      return;
    }
    const gen = genRef.current;
    const shouldCancel = () => gen !== genRef.current;
    setLoadingMore(true);
    setSearchError(null);
    try {
      const page = await searchPage({
        query: trimmed,
        mode,
        limit: morePageLimit,
        offset: results.length,
        fallback_0243_mode: fallback0243Mode,
        ui_lang: uiLang,
        shouldCancel,
      });
      if (shouldCancel()) return;
      setResults((prev) => [...prev, ...page.items]);
      if (page.total != null) {
        setTotal(page.total);
      }
      setLastPageSize(page.items.length);
    } catch (err) {
      if (shouldCancel() || isSearchCancelledError(err)) return;
      setSearchError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      if (!shouldCancel()) {
        setLoadingMore(false);
      }
    }
  }, [
    canSearch,
    loading,
    loadingMore,
    hasMore,
    trimmed,
    mode,
    morePageLimit,
    results.length,
    fallback0243Mode,
    uiLang,
  ]);

  return {
    results,
    total,
    hint,
    loading: isLoading,
    loadingVisible,
    loadingMore,
    error: searchError,
    isReady,
    hasMore,
    loadMore,
  };
}

export default useDB;