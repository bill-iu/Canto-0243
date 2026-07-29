import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import type { QueryTab } from '@shared/query-tabs';
import { isPortableHost } from '../host-mode.ts';
import { searchLimitForOffset, searchPage, type QueryResult } from '../db/query.ts';
import { useDebouncedSearchQuery } from '../hooks/useDebouncedSearchQuery.ts';
import { countWorkspaceRender, markSearchDispatch, markSearchResolve } from '../search-perf.ts';
import type { Last0243SearchMode, PingzeSubMode, UiMode } from '../mode-meta.ts';
import type { QueryWorkspaceNavigationAdapter } from './navigation-adapter.ts';
import {
  filterByProjectPos,
  isPosFilterActive,
  normalizePosFilter,
  type PosFilterState,
} from '../pos/filter.ts';
import {
  createDatabaseQueryWorkspaceAdapter,
  createPortableQueryWorkspaceAdapter,
  type QueryWorkspaceQueryAdapter,
} from './query-engine-adapter.ts';
import {
  createInitialQueryWorkspaceState,
  reduceQueryWorkspace,
  snapshotFromQueryWorkspace,
  type QueryWorkspaceSnapshot,
} from './state.ts';
import { buildPresentationCheckpoint } from './presentation.ts';
import { useQueryWorkspaceDetail } from './useQueryWorkspaceDetail.ts';
import { mergePickLookupResults } from '../../../shared/entry-detail-core.mjs';
import { mergeShuffledResults, shuffleResults } from '../shuffle-results.ts';

const SEARCH_LOADING_LABEL_DELAY_MS = 150;

export interface UseQueryWorkspaceOptions {
  activeTab: QueryTab | null;
  enabled: boolean;
  isReady: boolean;
  mode: UiMode;
  pzmode: PingzeSubMode;
  fallback0243Mode: Last0243SearchMode;
  uiLang: 'zh' | 'zh-Hans' | 'en';
  dataVersion: string;
  rhymeProfile?: string;
  navigationAdapter?: QueryWorkspaceNavigationAdapter;
}

function snapshotFromTab(
  tab: QueryTab,
  fallbackMode: UiMode,
  fallbackPzMode: PingzeSubMode,
  dataVersion: string,
): QueryWorkspaceSnapshot<QueryResult> {
  const cacheIsCurrent = tab.dataVersion === dataVersion;
  return {
    tabId: tab.id,
    q: tab.q || '',
    results: cacheIsCurrent ? (tab.results as QueryResult[]) || [] : [],
    offset: cacheIsCurrent ? tab.offset || 0 : 0,
    total: cacheIsCurrent ? tab.total ?? null : null,
    mode: (tab.mode as UiMode | undefined) ?? fallbackMode,
    pzmode: (tab.pzmode as PingzeSubMode | undefined) ?? fallbackPzMode,
    shuffled: cacheIsCurrent && Boolean(tab.shuffled),
    scrollTop: Number.isFinite(tab.scrollTop) ? Math.max(0, tab.scrollTop ?? 0) : 0,
    dataVersion,
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
  dataVersion,
  rhymeProfile = 'exact',
  navigationAdapter,
}: UseQueryWorkspaceOptions) {
  countWorkspaceRender();
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
  const [presentationResults, setPresentationResultsState] = useState<QueryResult[]>([]);
  const [presentationShuffled, setPresentationShuffledState] = useState(false);
  const [presentationGeneration, setPresentationGeneration] = useState(0);
  const presentationTabIdRef = useRef<number | null>(null);
  const presentationResultsRef = useRef<QueryResult[]>([]);
  const presentationShuffledRef = useRef(false);
  const [loadingVisible, setLoadingVisible] = useState(false);
  const activatedTabRef = useRef<string | null>(null);
  const activeRequestIdRef = useRef<number | null>(null);
  const requestSequenceRef = useRef(0);
  const frameAbortRef = useRef<AbortController | null>(null);
  const loadMoreAbortRef = useRef<AbortController | null>(null);
  const commitKeyRef = useRef<string | null>(null);
  const presentationKeyRef = useRef('');
  const pickAnchorRef = useRef<string | null>(null);
  const pickAnchorRowsRef = useRef<QueryResult[]>([]);
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
      presentationTabIdRef.current = null;
      presentationResultsRef.current = [];
      presentationShuffledRef.current = false;
      setPresentationResultsState([]);
      setPresentationShuffledState(false);
      setPresentationGeneration((generation) => generation + 1);
      dispatch({ type: 'leave' });
      hydrateSearch('');
      return;
    }
    const activationKey = `${activeTabId}\0${dataVersion}`;
    if (activatedTabRef.current === activationKey) return;
    activatedTabRef.current = activationKey;
    frameAbortRef.current?.abort();
    loadMoreAbortRef.current?.abort();
    const snapshot = snapshotFromTab(activeTab, mode, pzmode, dataVersion);
    presentationTabIdRef.current = activeTabId;
    presentationResultsRef.current = [...snapshot.results];
    presentationShuffledRef.current = snapshot.shuffled;
    setPresentationResultsState([...snapshot.results]);
    setPresentationShuffledState(snapshot.shuffled);
    setPresentationGeneration((generation) => generation + 1);
    dispatch({ type: 'activateTab', snapshot });
    hydrateSearch(activeTab.q || '');
  }, [activeTab, activeTabId, dataVersion, hydrateSearch, mode, pzmode]);

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
        rhyme_profile: rhymeProfile,
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
  }, [adapter, enabled, fallback0243Mode, isReady, state.activeFrame, uiLang, rhymeProfile]);

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
        rhyme_profile: rhymeProfile,
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
  }, [adapter, enabled, fallback0243Mode, hasMore, isReady, morePageLimit, state, uiLang, rhymeProfile]);

  const filteredResultCount = useMemo(
    () => filterByProjectPos(state.results, (row) => row.word, state.posFilter).length,
    [state.posFilter, state.results],
  );

  useEffect(() => {
    if (
      !enabled ||
      !isReady ||
      !isPosFilterActive(state.posFilter) ||
      isLoading ||
      !hasMore ||
      state.results.length === 0 ||
      filteredResultCount >= 40
    ) {
      return;
    }
    void loadMore();
  }, [enabled, filteredResultCount, hasMore, isLoading, isReady, loadMore, state.posFilter, state.results.length]);

  useEffect(() => {
    if (!navigationAdapter || state.tabId == null || state.status !== 'ready') return;
    const checkpoint = buildPresentationCheckpoint(
      snapshotFromQueryWorkspace(state),
      presentationTabIdRef.current,
      presentationResultsRef.current,
      presentationShuffledRef.current,
    );
    if (checkpoint) {
      navigationAdapter.checkpoint(state.tabId, checkpoint);
    }
  }, [navigationAdapter, presentationGeneration, presentationResults, state]);

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
      navigationAdapter?.commit({ query, mode: nextMode, pzmode: nextPzMode });
    }, [flushSearchQuery, inputQuery, mode, navigationAdapter, pzmode],
  );

  const setFilter = useCallback((posFilter: PosFilterState) => {
    dispatch({ type: 'setFilter', posFilter: normalizePosFilter(posFilter) });
  }, []);

  const presentResults = useCallback((items: readonly QueryResult[]) => {
    const next = [...items];
    presentationResultsRef.current = next;
    setPresentationResultsState(next);
  }, []);

  const presentShuffledResults = useCallback((items: readonly QueryResult[]) => {
    const next = [...items];
    presentationResultsRef.current = next;
    presentationShuffledRef.current = true;
    setPresentationResultsState(next);
    setPresentationShuffledState(true);
    setPresentationGeneration((generation) => generation + 1);
  }, []);

  const clearPresentationShuffle = useCallback(() => {
    presentationShuffledRef.current = false;
    setPresentationShuffledState(false);
  }, []);

  useEffect(() => {
    const key = `${state.activeFrame?.query ?? state.draftQuery}\0${state.mode}\0${state.pzmode}`;
    if (presentationKeyRef.current !== key) {
      presentationKeyRef.current = key;
      clearPresentationShuffle();
    }
  }, [clearPresentationShuffle, state.activeFrame?.query, state.draftQuery, state.mode, state.pzmode]);

  useEffect(() => {
    const anchor = pickAnchorRef.current;
    if (anchor && state.draftQuery.trim() === anchor && !presentationShuffled) {
      if (!isLoading) {
        presentResults(
          mergePickLookupResults(anchor, pickAnchorRowsRef.current, state.results) as QueryResult[],
        );
        pickAnchorRef.current = null;
        pickAnchorRowsRef.current = [];
      }
      return;
    }
    if (!presentationShuffled) {
      presentResults(state.results);
      return;
    }
    presentResults(mergeShuffledResults(presentationResultsRef.current, state.results));
  }, [isLoading, presentResults, presentationShuffled, state.draftQuery, state.results]);

  const showPickAnchor = useCallback((literal: string, rows: readonly QueryResult[]) => {
    pickAnchorRef.current = literal;
    pickAnchorRowsRef.current = [...rows];
    presentResults(rows);
    hydrateSearch(literal);
  }, [hydrateSearch, presentResults]);

  const waitForPickMerge = useCallback(async (signal: AbortSignal) => {
    while (pickAnchorRef.current && !signal.aborted) {
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
  }, []);

  const shuffle = useCallback(() => {
    presentShuffledResults(shuffleResults([...state.results]));
  }, [presentShuffledResults, state.results]);

  const detail = useQueryWorkspaceDetail({
    activeTab: activeTab?.view === 'search' ? activeTab : null,
    isReady,
    waitForPickMerge,
  });

  const controls = {
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    setInputQueryLive,
    flushSearchQuery,
    hydrateSearch,
    commitSearch,
  };

  const resultsModel = {
    rows: state.results,
    total: state.total,
    hint: state.hint,
    loading: isLoading,
    loadingVisible,
    loadingMore: state.status === 'loading-more',
    error: state.error ? new Error(state.error) : null,
    hasMore,
    posFilter: state.posFilter,
    displayRows: presentationResults,
    shuffled: presentationShuffled,
    shuffleGeneration: presentationGeneration,
  };

  const resultsActions = {
    loadMore,
    setFilter,
    showPickAnchor,
    waitForPickMerge,
    shuffle,
  };
  const detailModel = {
    open: detail.open,
    model: detail.model,
    relationsLoading: detail.relationsLoading,
    literal: detail.literal,
    preferredJyutping: detail.preferredJyutping,
  };
  const detailActions = {
    close: detail.close,
    saveActive: detail.saveActive,
    forgetTab: detail.forgetTab,
    openLiteral: detail.openLiteral,
    openFromPick: detail.openFromPick,
  };

  return {
    controls,
    resultsModel,
    resultsActions,
    detailModel,
    detailActions,
  };
}
