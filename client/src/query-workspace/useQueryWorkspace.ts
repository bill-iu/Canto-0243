import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import type { QueryTab } from '@shared/query-tabs';
import { isPortableHost } from '../host-mode.ts';
import { searchLimitForOffset, searchPage, type QueryResult } from '../db/query.ts';
import { useDebouncedSearchQuery } from '../hooks/useDebouncedSearchQuery.ts';
import { markSearchDispatch, markSearchResolve } from '../search-perf.ts';
import type { Last0243SearchMode, PingzeSubMode, UiMode } from '../mode-meta.ts';
import type { PosFilterState } from '../pos/filter.ts';
import {
  createDatabaseQueryWorkspaceAdapter,
  createPortableQueryWorkspaceAdapter,
  type QueryWorkspaceQueryAdapter,
} from './query-engine-adapter.ts';
import {
  createInitialQueryWorkspaceState,
  reduceQueryWorkspace,
  type QueryWorkspaceSnapshot,
} from './state.ts';

const SEARCH_LOADING_LABEL_DELAY_MS = 150;

export interface UseQueryWorkspaceOptions {
  activeTab: QueryTab | null;
  enabled: boolean;
  isReady: boolean;
  mode: UiMode;
  pzmode: PingzeSubMode;
  fallback0243Mode: Last0243SearchMode;
  uiLang: 'zh' | 'zh-Hans' | 'en';
  onPatchTab?: (tabId: number, snapshot: Partial<QueryWorkspaceSnapshot<QueryResult>>) => void;
}

function snapshotFromTab(tab: QueryTab): QueryWorkspaceSnapshot<QueryResult> {
  return {
    tabId: tab.id,
    q: tab.q || '',
    results: (tab.results as QueryResult[]) || [],
    offset: tab.offset || 0,
    total: tab.total ?? null,
    posFilter: {
      pos: [...(tab.posFilter?.pos ?? [])] as QueryWorkspaceSnapshot<QueryResult>['posFilter']['pos'],
      family: [...(tab.posFilter?.family ?? [])] as QueryWorkspaceSnapshot<QueryResult>['posFilter']['family'],
      voice: [...(tab.posFilter?.voice ?? [])] as QueryWorkspaceSnapshot<QueryResult>['posFilter']['voice'],
    },
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function useQueryWorkspace({
  activeTab,
  enabled,
  isReady,
  mode,
  pzmode,
  fallback0243Mode,
  uiLang,
  onPatchTab,
}: UseQueryWorkspaceOptions) {
  const activeTabId = activeTab?.view === 'search' ? activeTab.id : null;
  const initialQuery = activeTab?.view === 'search' ? activeTab.q || '' : '';
  const {
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    setInputQueryLive,
    flushSearchQuery,
    hydrateSearch,
  } = useDebouncedSearchQuery(initialQuery);
  const [state, dispatch] = useReducer(
    reduceQueryWorkspace<QueryResult>,
    undefined,
    createInitialQueryWorkspaceState<QueryResult>,
  );
  const [loadingVisible, setLoadingVisible] = useState(false);
  const activatedTabRef = useRef<number | null>(null);
  const activeRequestIdRef = useRef<number | null>(null);
  const requestSequenceRef = useRef(0);
  const frameAbortRef = useRef<AbortController | null>(null);
  const loadMoreAbortRef = useRef<AbortController | null>(null);
  const commitKeyRef = useRef<string | null>(null);
  activeRequestIdRef.current = state.activeRequestId;

  const adapter = useMemo<QueryWorkspaceQueryAdapter>(
    () =>
      isPortableHost()
        ? createPortableQueryWorkspaceAdapter()
        : createDatabaseQueryWorkspaceAdapter(searchPage),
    [],
  );

  useEffect(() => {
    if (activeTabId == null || !activeTab || activeTab.view !== 'search') {
      activatedTabRef.current = null;
      frameAbortRef.current?.abort();
      loadMoreAbortRef.current?.abort();
      dispatch({ type: 'leave' });
      hydrateSearch('');
      return;
    }
    if (activatedTabRef.current === activeTabId) return;
    activatedTabRef.current = activeTabId;
    frameAbortRef.current?.abort();
    loadMoreAbortRef.current?.abort();
    dispatch({ type: 'activateTab', snapshot: snapshotFromTab(activeTab) });
    hydrateSearch(activeTab.q || '');
  }, [activeTab, activeTabId, hydrateSearch]);

  useEffect(() => {
    if (!enabled || !isReady || activeTabId == null || !searchQuery.trim()) {
      frameAbortRef.current?.abort();
      loadMoreAbortRef.current?.abort();
      if (activeTabId != null && !searchQuery.trim()) {
        dispatch({ type: 'clearQuery', query: searchQuery });
      }
      return;
    }

    const key = `${searchQuery.trim()}\0${mode}\0${pzmode}`;
    if (commitKeyRef.current === key) {
      commitKeyRef.current = null;
      return;
    }
    dispatch({
      type: 'beginFrame',
      query: searchQuery.trim(),
      mode,
      pzmode,
      kind: 'preview',
    });
  }, [activeTabId, enabled, fallback0243Mode, isReady, mode, pzmode, searchQuery, uiLang]);

  useEffect(() => {
    const frame = state.activeFrame;
    if (
      !enabled ||
      !isReady ||
      !frame ||
      activeRequestIdRef.current != null ||
      !frame.query.trim()
    ) {
      return;
    }

    frameAbortRef.current?.abort();
    const controller = new AbortController();
    frameAbortRef.current = controller;
    const frameId = frame.id;
    const requestId = ++requestSequenceRef.current;
    dispatch({ type: 'requestStarted', frameId, requestId, append: false });
    markSearchDispatch();

    void adapter
      .searchPage({
        query: frame.query,
        mode: frame.mode as Parameters<typeof searchLimitForOffset>[0],
        limit: searchLimitForOffset(frame.mode as Parameters<typeof searchLimitForOffset>[0], 0),
        offset: 0,
        fallback_0243_mode: fallback0243Mode,
        pzmode: frame.pzmode as PingzeSubMode,
        ui_lang: uiLang,
        signal: controller.signal,
      })
      .then((page) => {
        if (!controller.signal.aborted) markSearchResolve();
        dispatch({
          type: 'requestResolved',
          frameId,
          requestId,
          items: page.items,
          total: page.total,
          hint: page.hint,
          append: false,
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        markSearchResolve();
        dispatch({
          type: 'requestRejected',
          frameId,
          requestId,
          message: errorMessage(error),
        });
      });

    return () => controller.abort();
  }, [adapter, enabled, fallback0243Mode, isReady, state.activeFrame, uiLang]);

  const isLoading = state.status === 'loading' || state.status === 'loading-more';
  useEffect(() => {
    if (!isLoading) {
      setLoadingVisible(false);
      return;
    }
    const timer = window.setTimeout(() => setLoadingVisible(true), SEARCH_LOADING_LABEL_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [isLoading]);

  const morePageLimit = searchLimitForOffset(mode, 1);
  const hasMore =
    enabled &&
    isReady &&
    Boolean(searchQuery.trim()) &&
    ((state.total != null && state.results.length < state.total) ||
      (state.total == null && state.lastPageSize >= morePageLimit));

  const loadMore = useCallback(async () => {
    const frame = state.activeFrame;
    if (
      !enabled ||
      !isReady ||
      !frame ||
      state.activeFrameId == null ||
      state.activeRequestId != null ||
      state.status === 'loading' ||
      state.status === 'loading-more' ||
      !hasMore
    ) {
      return;
    }
    loadMoreAbortRef.current?.abort();
    const controller = new AbortController();
    loadMoreAbortRef.current = controller;
    const frameId = frame.id;
    const requestId = ++requestSequenceRef.current;
    dispatch({ type: 'requestStarted', frameId, requestId, append: true });
    try {
      const page = await adapter.searchPage({
        query: frame.query,
        mode: frame.mode as Parameters<typeof searchLimitForOffset>[0],
        limit: morePageLimit,
        offset: state.results.length,
        fallback_0243_mode: fallback0243Mode,
        pzmode: frame.pzmode as PingzeSubMode,
        ui_lang: uiLang,
        signal: controller.signal,
      });
      dispatch({
        type: 'requestResolved',
        frameId,
        requestId,
        items: page.items,
        total: page.total,
        hint: page.hint,
        append: true,
      });
    } catch (error) {
      if (controller.signal.aborted || isAbortError(error)) return;
      dispatch({
        type: 'requestRejected',
        frameId,
        requestId,
        message: errorMessage(error),
      });
    }
  }, [adapter, enabled, fallback0243Mode, hasMore, isReady, morePageLimit, state, uiLang]);

  useEffect(() => {
    if (!onPatchTab || state.tabId == null || state.status !== 'ready') return;
    onPatchTab(state.tabId, {
      q: state.draftQuery,
      results: state.results,
      total: state.total,
      offset: state.offset,
      posFilter: state.posFilter,
    });
  }, [onPatchTab, state]);

  const commitSearch = useCallback(
    (nextQuery = inputQuery, nextMode = mode, nextPzMode = pzmode) => {
      const query = nextQuery.trim();
      if (!query) {
        frameAbortRef.current?.abort();
        loadMoreAbortRef.current?.abort();
        flushSearchQuery(nextQuery);
        dispatch({ type: 'clearQuery', query: nextQuery });
        return;
      }
      frameAbortRef.current?.abort();
      loadMoreAbortRef.current?.abort();
      commitKeyRef.current = `${query}\0${nextMode}\0${nextPzMode}`;
      flushSearchQuery(nextQuery);
      dispatch({
        type: 'beginFrame',
        query,
        mode: nextMode,
        pzmode: nextPzMode,
        kind: 'commit',
      });
    }, [flushSearchQuery, inputQuery, mode, pzmode],
  );

  const setFilter = useCallback((posFilter: PosFilterState) => {
    dispatch({ type: 'setFilter', posFilter });
  }, []);

  return {
    ...state,
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    setInputQueryLive,
    flushSearchQuery,
    hydrateSearch,
    loading: isLoading,
    loadingVisible,
    loadingMore: state.status === 'loading-more',
    error: state.error ? new Error(state.error) : null,
    isReady,
    hasMore,
    loadMore,
    commitSearch,
    setFilter,
  };
}
