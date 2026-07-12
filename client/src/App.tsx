/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useDB, useSearch } from './hooks/useDB.ts';
import { getActiveDbBackendMode } from './db/init';
import { useQueryExplain } from './hooks/useQueryExplain.tsx';
import { useDebouncedSearchQuery } from './hooks/useDebouncedSearchQuery.ts';
import { useEntryDetailInset } from './hooks/useEntryDetailInset.ts';
import { ResultList } from './result-list';
import { mergedResultCount, type EntryPickPayload } from './result-list-logic.ts';
import { EntryDetailPanel } from './entry-detail/EntryDetailPanel';
import {
  enrichEntryDetailFromDb,
  enrichEntryDetailRelations,
  getCachedEntryDetail,
  hasDirectRelationSources,
  instantEntryDetailModel,
  loadEntryDetailCore,
} from './entry-detail/load-entry-detail';
import type { EntryDetailModel } from './entry-detail/types';
import {
  anchorOnlyQueryRow,
  mergePickLookupResults,
  pickReadingsToQueryRows,
  resolveListClickAction,
} from '../../frontend/entry-detail-core.mjs';
import { SynResultList } from './syn-result-list';
import { synResultItemCount, synResultsStats } from './syn-result-logic.ts';
import { AnchorResultList } from './anchor-result-list';
import {
  anchorResultItemCount,
  anchorResultsStats,
  hasAnchorResultLayout,
} from './anchor-result-logic.ts';
import { useInfiniteResultWindow } from './infinite-results';
import { formatEmptySearchMessage } from './empty-search-message';
import { isRelationSyntaxQuery } from './db/query-engine';
import { GuideQuick } from './guide-quick';
import { GuideView } from './guide-view';
import { AboutView } from './about-view';
import { ModeMenu } from './mode-menu';
import type { GuideMode } from './guide-examples';
import { mergeShuffledResults, shuffleResults } from './shuffle-results';
import { ShuffleIcon } from './shuffle-icon';
import type { QueryResult } from './db/query';
import {
  last0243UiToUrlMode,
  getModeMeta,
  modeMetaFor,
  modeRedirectHint,
  type PingzeSubMode,
  type Last0243SearchMode,
  type UiMode,
} from './mode-meta';
import { parseSearchUrl } from './search-url';
import { profileToUiMode, searchFamilyForUiMode, uiModeToProfile } from '../../contracts/search-mode-manifest.mjs';
import { BrandSvgDefs } from './brand-svg-defs';
import { BrandLogo } from './brand-logo';
import { ReadyGate } from './ready-gate';
import { hasPwaGateLanded } from './pwa-shell-boot';
import { usePwaInstallPrompt } from './hooks/usePwaInstallPrompt';
import { PwaInstallBanner } from './components/PwaInstallBanner';
import { TailPreloadBadge } from './components/TailPreloadBadge';
import { QueryTabsBar } from './query-tabs/query-tabs-bar';
import { useQueryTabs, VIEW } from './query-tabs/useQueryTabs';
import { getLang, setLang, getTheme, setTheme, SEARCH_RING_BLUR_MS } from '../../frontend/app-context.mjs';

const initialUrl =
  typeof window !== 'undefined'
    ? parseSearchUrl(window.location.search)
    : { q: '', mode: '0243' as UiMode, pzmode: 'm1' as PingzeSubMode, view: 'search' as const };

function App() {
  const lexiconVersion = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  const conn = (navigator as any).connection;
  const isLikelyMetered =
    Boolean(conn?.saveData) ||
    (typeof conn?.effectiveType === 'string' && /(^|-)2g$/.test(conn.effectiveType));

  const [mode, setMode] = useState<UiMode>(initialUrl.mode);
  const [pzMode, setPzMode] = useState<PingzeSubMode>(initialUrl.pzmode);
  const [last0243Mode, setLast0243Mode] = useState<Last0243SearchMode>(() => {
    if (initialUrl.mode === '02493') return '02493';
    if (initialUrl.mode === '394052') return '394052';
    return '0243';
  });

  const {
    tabState,
    activeTab,
    tabs,
    selectTab,
    addSearchTab,
    openSearchTabWithQuery,
    closeTab,
    reorderTabs,
    openGuide,
    openAbout,
    goHome,
    ensureActiveSearchTab,
    patchSearchTab,
    commitActiveSearch,
    popstateFrame,
    consumePopstateFrame,
    needsInitialSearch,
    initialBootstrap,
  } = useQueryTabs({
    currentMode: mode,
    currentPzMode: pzMode,
    onModeChange: (next, nextPzMode) => {
      setMode(next);
      if (nextPzMode) setPzMode(nextPzMode);
    },
  });

  const activeSearchTab = activeTab?.view === VIEW.SEARCH ? activeTab : null;
  const view =
    activeTab?.view === VIEW.GUIDE
      ? 'guide'
      : activeTab?.view === VIEW.ABOUT
        ? 'about'
        : 'search';

  const {
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    flushSearchQuery,
    hydrateSearch,
  } = useDebouncedSearchQuery(activeSearchTab?.q ?? '');

  const [useLiveFetch, setUseLiveFetch] = useState(true);
  const [redirectHint, setRedirectHint] = useState<string | null>(null);
  const [displayResults, setDisplayResults] = useState<QueryResult[]>([]);
  const [cachedTotal, setCachedTotal] = useState<number | null>(null);
  const [resultsShuffled, setResultsShuffled] = useState(false);
  const [shuffleGeneration, setShuffleGeneration] = useState(0);
  const [gateOpen, setGateOpen] = useState(() => !hasPwaGateLanded());
  const [warmupBadgeClear, setWarmupBadgeClear] = useState(false);
  const [uiLang, setUiLang] = useState<'zh' | 'en'>(() => getLang() as 'zh' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(
    () => getTheme({ defaultTheme: 'dark' }) as 'light' | 'dark',
  );
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailModel, setDetailModel] = useState<EntryDetailModel | null>(null);
  const [detailRelationsLoading, setDetailRelationsLoading] = useState(false);
  const [activeDetailLiteral, setActiveDetailLiteral] = useState<string | null>(null);
  const [preferredJyutping, setPreferredJyutping] = useState<string | null>(null);
  const [searchRingClass, setSearchRingClass] = useState('');
  const searchRingBlurTimerRef = useRef<number | null>(null);
  const detailLoadGenRef = useRef(0);
  const lastPickReadingsRef = useRef<EntryPickPayload['readings']>(undefined);
  const pickAnchorRef = useRef<string | null>(null);
  const pickAnchorRowsRef = useRef<QueryResult[]>([]);

  useEntryDetailInset(detailOpen);
  const searchKeyRef = useRef('');
  const activeTabIdRef = useRef<number | null>(null);
  const syncedTabIdRef = useRef<number | null>(null);
  const initialSearchDoneRef = useRef(false);
  const lexiconLoadStartedRef = useRef(false);

  const trimmedInput = inputQuery.trim();
  const relationSyntax = trimmedInput ? isRelationSyntaxQuery(trimmedInput) : false;
  const searchKey = `${searchQuery}\0${mode}\0${pzMode}`;
  const modeMeta = modeMetaFor(mode, uiLang);

  const loadSearchTabUi = useCallback(
    (tab: typeof activeTab, live: boolean) => {
      if (!tab || tab.view !== VIEW.SEARCH) return;
      // Keep unsynced until searchQuery catches up — marking synced here lets a
      // stale empty query from the previous tab overwrite this tab's title/q.
      syncedTabIdRef.current = null;
      hydrateSearch(tab.q || '');
      const useLive = live || initialBootstrap.forceLive;
      setUseLiveFetch(useLive);
      setResultsShuffled(false);
      if (!useLive) {
        const cached = (tab.results as QueryResult[]) || [];
        setDisplayResults(cached);
        setCachedTotal(tab.total ?? null);
      } else {
        // New / live tab: clear prior tab's chips until results arrive
        setDisplayResults([]);
        setCachedTotal(null);
      }
    },
    [hydrateSearch, initialBootstrap.forceLive],
  );

  useEffect(() => {
    if (!activeTab) return;
    if (activeTabIdRef.current === activeTab.id) return;
    activeTabIdRef.current = activeTab.id;
    if (activeTab.view === VIEW.SEARCH) {
      const hasCache =
        !initialBootstrap.forceLive && ((activeTab.results as QueryResult[]) || []).length > 0;
      loadSearchTabUi(activeTab, !hasCache);
    } else {
      syncedTabIdRef.current = activeTab.id;
    }
  }, [activeTab, loadSearchTabUi, initialBootstrap.forceLive]);

  useEffect(() => {
    if (!trimmedInput) {
      setRedirectHint(null);
      return;
    }
    if (relationSyntax) {
      setRedirectHint(modeRedirectHint(last0243UiToUrlMode(last0243Mode), uiLang));
      if (mode === 'synonym') {
        setMode(last0243Mode);
      }
      return;
    }
    setRedirectHint(null);
  }, [trimmedInput, relationSyntax, mode, last0243Mode, uiLang]);

  const {
    isReady,
    offlineStatus,
    isOnline,
    isDbCached,
    progress,
    tailProgress,
    startupComplete,
    suppressGateOverlay,
    error: dbError,
    initialize,
    retryOfflineReady,
  } = useDB();

  const { hasNativePrompt, trigger } = usePwaInstallPrompt();

  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as any).standalone === true;

  const [installDismissed, setInstallDismissed] = useState(
    () => !!sessionStorage.getItem('canto-pwa-install-dismissed')
  );

  const shellGated = offlineStatus !== 'ready' || gateOpen;

  const shouldShowInstallBanner =
    !shellGated && !isStandalone && !installDismissed;

  // Apply theme + lang (shared with vanilla via app-context)
  useEffect(() => {
    setTheme(uiTheme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', uiTheme === 'dark' ? '#1C1917' : '#EBDFD0');
  }, [uiTheme]);

  useEffect(() => {
    setLang(uiLang);
    document.documentElement.lang = uiLang === 'zh' ? 'zh-Hant' : 'en';
  }, [uiLang]);

  const {
    results,
    total,
    hint: searchHint,
    loading: searchLoading,
    loadingVisible: searchLoadingVisible,
    loadingMore,
    error: searchError,
    hasMore,
    loadMore,
  } = useSearch(useLiveFetch ? searchQuery : '', mode, {
    fallback_0243_mode: last0243Mode,
    pzmode: pzMode,
    ui_lang: uiLang,
  });

  const saveLeavingSearchTab = useCallback(() => {
    const leavingId = tabState.activeId;
    const leaving = tabState.tabs.find((t) => t.id === leavingId);
    if (leaving?.view !== VIEW.SEARCH) return;
    patchSearchTab(leavingId, {
      q: inputQuery,
      results: displayResults,
      total: useLiveFetch ? total : cachedTotal,
      offset: displayResults.length,
    });
  }, [
    tabState.activeId,
    tabState.tabs,
    inputQuery,
    displayResults,
    useLiveFetch,
    total,
    cachedTotal,
    patchSearchTab,
  ]);

  useEffect(() => {
    if (!activeTab || activeTab.view !== VIEW.SEARCH || !useLiveFetch) return;
    if (searchQuery === (activeTab.q || '').trim()) {
      syncedTabIdRef.current = activeTab.id;
    }
  }, [activeTab, searchQuery, useLiveFetch]);

  useEffect(() => {
    if (searchKeyRef.current !== searchKey) {
      searchKeyRef.current = searchKey;
      setResultsShuffled(false);
    }
  }, [searchKey]);

  useEffect(() => {
    if (!useLiveFetch) return;
    const anchor = pickAnchorRef.current;
    if (anchor && searchQuery.trim() === anchor && !resultsShuffled) {
      if (!searchLoading) {
        setDisplayResults(
          mergePickLookupResults(anchor, pickAnchorRowsRef.current, results) as QueryResult[],
        );
        pickAnchorRef.current = null;
        pickAnchorRowsRef.current = [];
      }
      return;
    }
    if (!resultsShuffled) {
      setDisplayResults(results);
      return;
    }
    setDisplayResults((prev) => mergeShuffledResults(prev, results));
  }, [results, resultsShuffled, useLiveFetch, searchLoading, searchQuery]);

  useEffect(() => {
    if (!useLiveFetch || view !== 'search' || searchLoading) return;
    if (!activeTab || activeTab.view !== VIEW.SEARCH) return;
    if (syncedTabIdRef.current !== activeTab.id) return;
    // Guard tab-switch race: searchQuery may still be the previous tab's value
    // for one render while activeTab already points at the restored tab.
    if (searchQuery !== (activeTab.q || '').trim()) return;
    patchSearchTab(activeTab.id, {
      q: searchQuery,
      results,
      total,
      offset: results.length,
    });
    setCachedTotal(total);
  }, [
    useLiveFetch,
    view,
    searchLoading,
    searchQuery,
    results,
    total,
    activeTab,
    patchSearchTab,
  ]);

  useEffect(() => {
    if (isReady || offlineStatus === 'error') return;
    if (lexiconLoadStartedRef.current) return;
    lexiconLoadStartedRef.current = true;
    void initialize();
  }, [isReady, offlineStatus, initialize]);

  useEffect(() => {
    if (initialSearchDoneRef.current || !needsInitialSearch || gateOpen || !isReady) return;
    initialSearchDoneRef.current = true;
    setUseLiveFetch(true);
    hydrateSearch(activeSearchTab?.q || '');
    flushSearchQuery(activeSearchTab?.q || '');
  }, [needsInitialSearch, isReady, gateOpen, activeSearchTab?.q, hydrateSearch, flushSearchQuery]);

  const { summary: explainSummary, warning: explainWarning } = useQueryExplain(inputQuery, mode);
  const showExplain = view === 'search' && Boolean(explainSummary || explainWarning);

  const displayHint = redirectHint || searchHint;
  const effectiveTotal = useLiveFetch ? total : cachedTotal;
  const mountWarmupBadge = !shellGated && !warmupBadgeClear;
  const handleWarmupBadgeDismiss = useCallback(() => setWarmupBadgeClear(true), []);

  useEffect(() => {
    if (shellGated) setWarmupBadgeClear(false);
  }, [shellGated]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && detailOpen) {
        setDetailOpen(false);
        setActiveDetailLiteral(null);
        setDetailModel(null);
        setPreferredJyutping(null);
        return;
      }
      if (!event.altKey || event.ctrlKey || event.metaKey) return;
      const key = event.key.toLowerCase();
      if (key === 'n') {
        event.preventDefault();
        saveLeavingSearchTab();
        addSearchTab();
        requestAnimationFrame(() => document.getElementById('searchInput')?.focus());
        return;
      }
      if (key === 'w') {
        event.preventDefault();
        saveLeavingSearchTab();
        closeTab(tabState.activeId);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [saveLeavingSearchTab, addSearchTab, closeTab, tabState.activeId, detailOpen]);

  const closeEntryDetail = useCallback(() => {
    detailLoadGenRef.current += 1;
    setDetailOpen(false);
    setActiveDetailLiteral(null);
    setDetailModel(null);
    setDetailRelationsLoading(false);
    setPreferredJyutping(null);
  }, []);

  const waitForPickMerge = useCallback(async (gen: number) => {
    while (pickAnchorRef.current && gen === detailLoadGenRef.current) {
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
  }, []);

  const scheduleEntryDetailEnrich = useCallback((base: EntryDetailModel, gen: number) => {
    const run = () => {
      void (async () => {
        await waitForPickMerge(gen);
        if (gen !== detailLoadGenRef.current || !isReady) return;
        const hasRelations = await hasDirectRelationSources(base.literal);
        if (gen !== detailLoadGenRef.current) return;
        const fromDb = await enrichEntryDetailFromDb(base);
        if (gen !== detailLoadGenRef.current) return;
        setDetailModel(fromDb);
        if (!hasRelations) {
          setDetailRelationsLoading(false);
          return;
        }
        setDetailRelationsLoading(true);
        const full = await enrichEntryDetailRelations(fromDb);
        if (gen !== detailLoadGenRef.current) return;
        setDetailModel(full);
        setDetailRelationsLoading(false);
      })();
    };
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(run, { timeout: 800 });
    } else {
      setTimeout(run, 32);
    }
  }, [isReady, waitForPickMerge]);

  const openEntryDetailFromPick = useCallback(
    (payload: EntryPickPayload) => {
      const gen = ++detailLoadGenRef.current;
      const literal = payload.literal.trim();
      lastPickReadingsRef.current = payload.readings;

      const cached = getCachedEntryDetail(literal);
      const instant = cached
        ? cached
        : payload.readings?.length
          ? instantEntryDetailModel(literal, payload.readings)
          : null;

      setDetailOpen(true);
      setActiveDetailLiteral(literal);
      setPreferredJyutping(payload.jyutping ?? null);
      setDetailModel(instant);
      setDetailRelationsLoading(false);

      if (cached || !isReady) {
        if (cached) setDetailRelationsLoading(false);
        return;
      }

      if (instant) {
        scheduleEntryDetailEnrich(instant, gen);
        return;
      }

      queueMicrotask(() => {
        void (async () => {
          const core = await loadEntryDetailCore(literal);
          if (gen !== detailLoadGenRef.current) return;
          setDetailModel(core);
          if (!core) {
            setDetailRelationsLoading(false);
            return;
          }
          scheduleEntryDetailEnrich(core, gen);
        })();
      });
    },
    [isReady, scheduleEntryDetailEnrich],
  );

  useEffect(() => {
    if (!detailOpen || !activeDetailLiteral || !isReady) return;
    if (detailModel?.literal === activeDetailLiteral) return;
    openEntryDetailFromPick({
      literal: activeDetailLiteral,
      jyutping: preferredJyutping ?? undefined,
      readings: lastPickReadingsRef.current,
    });
  }, [detailOpen, activeDetailLiteral, isReady, detailModel?.literal, preferredJyutping, openEntryDetailFromPick]);

  useEffect(() => {
    if (!initialBootstrap.isHome) return;
    closeEntryDetail();
    hydrateSearch('');
    setUseLiveFetch(false);
    setDisplayResults([]);
    setCachedTotal(null);
  }, [initialBootstrap.isHome, hydrateSearch, closeEntryDetail]);

  useEffect(() => {
    if (!popstateFrame) return;
    setMode(popstateFrame.mode);
    setPzMode(popstateFrame.pzmode);
    if (popstateFrame.q) {
      setUseLiveFetch(true);
      hydrateSearch(popstateFrame.q);
      flushSearchQuery(popstateFrame.q);
    } else {
      closeEntryDetail();
      setUseLiveFetch(false);
      hydrateSearch('');
      setDisplayResults([]);
      setCachedTotal(null);
    }
    consumePopstateFrame();
  }, [popstateFrame, hydrateSearch, flushSearchQuery, consumePopstateFrame, closeEntryDetail]);

  const runCommittedSearch = useCallback(
    (nextQuery?: string, nextPzMode = pzMode, nextMode = mode) => {
      const q = (nextQuery ?? inputQuery).trim();
      if (pickAnchorRef.current && pickAnchorRef.current !== q) {
        pickAnchorRef.current = null;
        pickAnchorRowsRef.current = [];
      }
      flushSearchQuery(q);
      setUseLiveFetch(true);
      setResultsShuffled(false);
      commitActiveSearch(q, nextMode, nextPzMode);
      if (q && !isReady && !lexiconLoadStartedRef.current && offlineStatus !== 'error') {
        lexiconLoadStartedRef.current = true;
        void initialize();
      }
    },
    [inputQuery, flushSearchQuery, commitActiveSearch, mode, pzMode, isReady, offlineStatus, initialize],
  );

  const beginPickSearch = useCallback(
    (payload: EntryPickPayload) => {
      const literal = payload.literal.trim();
      const anchorRows = payload.readings?.length
        ? (pickReadingsToQueryRows(literal, payload.readings) as QueryResult[])
        : (anchorOnlyQueryRow(literal) as QueryResult[]);
      pickAnchorRef.current = literal;
      pickAnchorRowsRef.current = anchorRows;
      setDisplayResults(anchorRows);
      setCachedTotal(null);
      runCommittedSearch(literal);
      hydrateSearch(literal);
      openEntryDetailFromPick(payload);
    },
    [hydrateSearch, openEntryDetailFromPick, runCommittedSearch],
  );

  const handleRetryOfflineReady = useCallback(async () => {
    lexiconLoadStartedRef.current = false;
    await retryOfflineReady();
  }, [retryOfflineReady]);

  const handleModeChange = (family: 'basic' | 'pingze' | 'synonym') => {
    const next = family === 'basic' ? last0243Mode : family === 'pingze' ? 'pingze' : 'synonym';
    setMode(next);
    if (view === 'guide') {
      ensureActiveSearchTab();
    }
    if (trimmedInput) {
      runCommittedSearch(undefined, pzMode, next);
    }
  };

  const handlePzModeChange = (next: PingzeSubMode) => {
    setPzMode(next);
    if (mode === 'pingze' && trimmedInput) {
      runCommittedSearch(undefined, next);
    }
  };

  const handleProfileChange = (profile: PingzeSubMode) => {
    if (mode === 'pingze') return handlePzModeChange(profile);
    const next = profileToUiMode(profile) as UiMode;
    setLast0243Mode(next as Last0243SearchMode);
    setMode(next);
    if (trimmedInput) runCommittedSearch(undefined, pzMode, next);
  };

  const handleBackToSearch = () => {
    ensureActiveSearchTab();
  };

  const handleRunExample = (nextQuery: string, exampleMode: GuideMode) => {
    if (exampleMode === '0243' || exampleMode === '02493' || exampleMode === '394052') {
      setLast0243Mode(exampleMode);
    }
    setMode(exampleMode);
    // 教學例子：開新搜尋 tab，唔覆蓋當前 tab
    saveLeavingSearchTab();
    openSearchTabWithQuery(nextQuery, exampleMode as UiMode, pzMode);
    setUseLiveFetch(true);
    setResultsShuffled(false);
  };

  const handleShuffle = () => {
    setDisplayResults(shuffleResults(results));
    setResultsShuffled(true);
    setShuffleGeneration((n) => n + 1);
  };

  const handleSubmit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    runCommittedSearch();
  };

  const handleReorderTabs = (fromIndex: number, toIndex: number) => {
    saveLeavingSearchTab();
    reorderTabs(fromIndex, toIndex);
  };

  const handleSelectTab = (id: number) => {
    saveLeavingSearchTab();
    selectTab(id);
  };

  const handleCloseTab = (id: number) => {
    saveLeavingSearchTab();
    closeTab(id);
  };

  const handleAddTab = () => {
    saveLeavingSearchTab();
    addSearchTab();
  };

  const handleOpenGuide = () => {
    saveLeavingSearchTab();
    openGuide();
  };

  const handleOpenAbout = () => {
    saveLeavingSearchTab();
    openAbout();
  };

  const handleSearchInput = (value: string) => {
    setInputQueryDebounced(value);
    if (activeTab?.view === VIEW.SEARCH) {
      patchSearchTab(tabState.activeId, { q: value });
    }
  };

  const handleSearchFocus = () => {
    if (searchRingBlurTimerRef.current != null) {
      window.clearTimeout(searchRingBlurTimerRef.current);
      searchRingBlurTimerRef.current = null;
    }
    setSearchRingClass('is-focused');
  };

  const handleSearchBlur = () => {
    setSearchRingClass('is-blurring');
    if (searchRingBlurTimerRef.current != null) {
      window.clearTimeout(searchRingBlurTimerRef.current);
    }
    searchRingBlurTimerRef.current = window.setTimeout(() => {
      setSearchRingClass('');
      searchRingBlurTimerRef.current = null;
    }, SEARCH_RING_BLUR_MS);
  };

  useEffect(
    () => () => {
      if (searchRingBlurTimerRef.current != null) {
        window.clearTimeout(searchRingBlurTimerRef.current);
      }
    },
    [],
  );

  const synLayout = mode === 'synonym';
  const anchorLayout = !synLayout && hasAnchorResultLayout(displayResults);
  const [scrollRootEl, setScrollRootEl] = useState<HTMLDivElement | null>(null);
  const infiniteScrollRoot = scrollRootEl;

  const resultItemCount = useMemo(() => {
    if (!displayResults.length) return 0;
    if (synLayout) return synResultItemCount(displayResults);
    if (anchorLayout) return anchorResultItemCount(displayResults);
    return mergedResultCount(displayResults);
  }, [displayResults, synLayout, anchorLayout]);

  const { visibleCount, sentinelRef, showSentinel } = useInfiniteResultWindow({
    itemCount: resultItemCount,
    hasMore: Boolean(useLiveFetch && hasMore),
    loading: searchLoading,
    loadingMore,
    onLoadMore: () => void loadMore(),
    resetKey: `${searchKey}\0${shuffleGeneration}`,
    scrollRoot: infiniteScrollRoot,
  });

  const handleEntryPick = useCallback(
    (payload: EntryPickPayload) => {
      if (mode === 'synonym') {
        runCommittedSearch(payload.literal);
        return;
      }
      const action = resolveListClickAction({
        panelOpen: detailOpen,
        activeLiteral: activeDetailLiteral,
        targetLiteral: payload.literal,
      });
      if (action === 'close') {
        closeEntryDetail();
        return;
      }
      if (action === 'open_only') {
        setDetailOpen(true);
        setActiveDetailLiteral(payload.literal);
        setPreferredJyutping(payload.jyutping ?? null);
        return;
      }
      beginPickSearch(payload);
    },
    [mode, detailOpen, activeDetailLiteral, closeEntryDetail, beginPickSearch, runCommittedSearch],
  );

  const handleRelationPick = useCallback(
    (literal: string) => {
      beginPickSearch({ literal });
    },
    [beginPickSearch],
  );

  const handleSearchMainClick = useCallback(
    (event: React.MouseEvent) => {
      if (!detailOpen) return;
      const target = event.target as HTMLElement;
      if (target.closest('.entry-detail-panel') || target.closest('.result-link')) return;
      closeEntryDetail();
    },
    [detailOpen, closeEntryDetail],
  );
  const statsSuffix = `（${modeMeta.statsLabel}）`;

  const resultsLabel = useMemo(() => {
    if (synLayout && displayResults.length > 0) {
      return `${synResultsStats(displayResults)}${statsSuffix}`;
    }
    if (anchorLayout && displayResults.length > 0) {
      return `${anchorResultsStats(displayResults, effectiveTotal)}${statsSuffix}`;
    }
    if (effectiveTotal != null && effectiveTotal > displayResults.length) {
      return `已載入 ${displayResults.length} / ${effectiveTotal} 個結果${statsSuffix}`;
    }
    if (displayResults.length > 0) {
      return `${displayResults.length} 個結果${statsSuffix}`;
    }
    return '';
  }, [synLayout, anchorLayout, displayResults, effectiveTotal, statsSuffix]);

  const emptyMessage = useMemo(() => {
    if (!searchQuery || searchLoading || displayResults.length > 0 || offlineStatus !== 'ready') {
      return null;
    }
    if (!useLiveFetch) return null;
    return formatEmptySearchMessage(searchQuery, displayHint, mode);
  }, [searchQuery, searchLoading, displayResults.length, offlineStatus, displayHint, mode, useLiveFetch]);

  const canShuffle = view === 'search' && displayResults.length > 0 && !searchLoading;
  const showGuideQuick =
    view === 'search' &&
    !trimmedInput &&
    !searchQuery.trim() &&
    displayResults.length === 0 &&
    !searchLoading &&
    !emptyMessage;
  const canSearch = !shellGated;

  const handleHome = () => {
    saveLeavingSearchTab();
    goHome();
    syncedTabIdRef.current = tabState.activeId;
    setUseLiveFetch(false);
    hydrateSearch('');
    setDisplayResults([]);
    setCachedTotal(null);
    setResultsShuffled(false);
  };

  return (
    <>
      <BrandSvgDefs />
      <ReadyGate
        offlineStatus={offlineStatus}
        progress={progress}
        errorMessage={dbError?.message}
        isOnline={isOnline}
        isDbCached={isDbCached}
        isLikelyMetered={isLikelyMetered}
        suppressGateOverlay={suppressGateOverlay}
        onRetry={handleRetryOfflineReady}
        onOpenChange={setGateOpen}
        theme={uiTheme}
      />
      <div
        className={`app-shell${shellGated ? ' is-gated' : ' is-revealing'}${warmupBadgeClear && !shellGated ? ' is-header-brand-ready' : ''}${shouldShowInstallBanner ? ' has-install-banner' : ''}${detailOpen ? ' has-entry-detail' : ''}`}
      >
        <header className="app-header">
          <div className="app-bar">
            <button className="brand" type="button" aria-label={uiLang === 'zh' ? '返回搜尋首頁' : 'Back to search home'} onClick={handleHome}>
              <BrandLogo variant="header" inkProgress={1} theme={uiTheme} />
            </button>
            <div className="header-hero">
              <h1 id="searchTitle">{uiLang === 'en' ? 'ONE-RUN-RHYME' : 'ONE·搵·韻'}</h1>
              <p className="header-hero__tagline">
                {uiLang === 'en'
                  ? 'Meter / sound match / rhyme / near-antonyms — find in one step.'
                  : '格律／協音／押韻／近反義，一步搵到。'}
              </p>
            </div>
            {mountWarmupBadge && (
              <TailPreloadBadge
                tailProgress={tailProgress}
                startupComplete={startupComplete}
                theme={uiTheme}
                lang={uiLang}
                onDismiss={handleWarmupBadgeDismiss}
              />
            )}
            <ModeMenu
              mode={mode}
              disabled={shellGated}
              onModeChange={handleModeChange}
              onOpenGuide={handleOpenGuide}
              onOpenAbout={handleOpenAbout}
              theme={uiTheme}
              lang={uiLang}
              onThemeChange={(next) => setUiTheme(next)}
              onLangChange={(next) => setUiLang(next)}
              lexiconVersion={lexiconVersion}
              showOpfsBackend={isReady && getActiveDbBackendMode() === 'opfs-vfs'}
            />
          </div>
          <QueryTabsBar
            tabs={tabs}
            activeId={tabState.activeId}
            lang={uiLang}
            onSelect={handleSelectTab}
            onClose={handleCloseTab}
            onAdd={handleAddTab}
            onReorder={handleReorderTabs}
          />
        </header>

        <main className="main-wrap">
          {view === 'guide' ? (
            <GuideView lang={uiLang} onPick={handleRunExample} />
          ) : view === 'about' ? (
            <AboutView lang={uiLang} lexiconVersion={lexiconVersion} onBack={handleBackToSearch} />
          ) : (
            <section
              className={`search-view${detailOpen ? ' has-entry-detail' : ''}${showGuideQuick ? ' is-empty-landing' : ''}`}
              aria-labelledby="searchTitle"
            >
              <div className="search-view__main" onClick={handleSearchMainClick}>
              <form onSubmit={handleSubmit} className="search-panel" role="search">
                <div className="field-label-row">
                  <label className="field-label" htmlFor="searchInput">
                    {uiLang === 'en' ? 'Search' : '搜尋內容'}
                  </label>
                  <span className="mode-readout" aria-live="polite">
                    {(uiLang === 'en' ? 'Current mode: ' : '目前模式：')}{modeMeta.readout}
                  </span>
                </div>
                <div className="search-row">
                  <div className={`search-input-wrap${searchRingClass ? ` ${searchRingClass}` : ''}`}>
                    <input
                      id="searchInput"
                      type="search"
                      value={inputQuery}
                      onChange={(e) => handleSearchInput(e.target.value)}
                      onFocus={handleSearchFocus}
                      onBlur={handleSearchBlur}
                      placeholder={modeMeta.placeholder}
                      disabled={shellGated}
                      autoComplete="off"
                      spellCheck={false}
                      enterKeyHint="search"
                    />
                  </div>
                  <div className="search-actions">
                    <button
                      type="button"
                      className="icon-button"
                      onClick={handleShuffle}
                      disabled={!canShuffle}
                      aria-label={uiLang === 'en' ? 'Shuffle results' : '隨機打亂結果'}
                      title={uiLang === 'en' ? 'Shuffle results' : '隨機打亂結果'}
                    >
                      <ShuffleIcon />
                    </button>
                    <button
                      type="submit"
                      className="primary-button"
                      disabled={!canSearch || !trimmedInput || (useLiveFetch && searchLoading)}
                      aria-busy={useLiveFetch && searchLoading}
                    >
                      {useLiveFetch && searchLoading
                        ? uiLang === 'en'
                          ? 'Searching…'
                          : '搜尋中…'
                        : uiLang === 'en'
                          ? 'Search'
                          : '搜尋'}
                    </button>
                  </div>
                </div>
                {searchFamilyForUiMode(mode) !== 'synonym' ? (
                  <div className="pingze-submodes" role="group" aria-label={uiLang === 'en' ? 'Ping-ze digit sub-mode' : '平仄數字子模式'}>
                    {(['m1', 'm2', 'm3'] as PingzeSubMode[]).map((subMode) => (
                      <button
                        key={subMode}
                        type="button"
                        className={`pingze-submode${(mode === 'pingze' ? pzMode : uiModeToProfile(mode)) === subMode ? ' is-active' : ''}`}
                        aria-pressed={(mode === 'pingze' ? pzMode : uiModeToProfile(mode)) === subMode}
                        disabled={shellGated}
                        onClick={() => handleProfileChange(subMode)}
                      >
                        <><span className="profile-pill__wide">{getModeMeta(subMode, uiLang).title}</span><span className="profile-pill__narrow">{subMode === 'm1' ? '四聲' : subMode === 'm2' ? '五聲' : '六聲'}</span></>
                      </button>
                    ))}
                  </div>
                ) : null}
              </form>

              {showExplain && (
                <p className="query-explain" aria-live="polite">
                  {explainSummary ? (
                    <span className="query-explain__summary">{explainSummary}</span>
                  ) : null}
                  {explainWarning ? (
                    <span className="query-explain__warning">{explainWarning}</span>
                  ) : null}
                </p>
              )}

              <div className="search-results">
                <div className="search-results-scroll" ref={setScrollRootEl}>
                  {displayHint && displayResults.length > 0 && (
                    <p className="search-hint">{displayHint}</p>
                  )}
                  {useLiveFetch && searchLoadingVisible && (
                    <p className="loading">{uiLang === 'en' ? 'Searching…' : '搜尋中…'}</p>
                  )}
                  {useLiveFetch && searchError && (
                    <p className="error">錯誤: {searchError.message}</p>
                  )}

                  {displayResults.length > 0 && (
                    <div className="results-list">
                      {resultsLabel ? <p className="results-count">{resultsLabel}</p> : null}
                      {synLayout ? (
                        <SynResultList
                          results={displayResults}
                          visibleLimit={visibleCount}
                          onPick={(word) => runCommittedSearch(word)}
                        />
                      ) : anchorLayout ? (
                        <AnchorResultList
                          results={displayResults}
                          visibleLimit={visibleCount}
                          activeLiteral={activeDetailLiteral}
                          lang={uiLang}
                          onPick={handleEntryPick}
                        />
                      ) : (
                        <ResultList
                          results={displayResults}
                          visibleLimit={visibleCount}
                          activeLiteral={activeDetailLiteral}
                          lang={uiLang}
                          onPick={handleEntryPick}
                        />
                      )}
                    </div>
                  )}

                  {emptyMessage && (
                    <div className="no-results info">
                      <p>
                        <strong>{emptyMessage.primary}</strong>
                      </p>
                      {emptyMessage.secondary ? <p>{emptyMessage.secondary}</p> : null}
                    </div>
                  )}

                  {showGuideQuick ? (
                    <GuideQuick
                      lang={uiLang}
                      disabled={shellGated || offlineStatus !== 'ready'}
                      onPick={handleRunExample}
                      onOpenFullGuide={handleOpenGuide}
                    />
                  ) : null}

                  {showSentinel ? (
                    <div ref={sentinelRef} className="results-scroll-sentinel" aria-hidden />
                  ) : null}
                </div>
              </div>
              </div>
            </section>
          )}
        </main>
      </div>

      {shouldShowInstallBanner && (
        <PwaInstallBanner
          hasNativePrompt={hasNativePrompt}
          onTrigger={trigger}
          onDismiss={() => setInstallDismissed(true)}
        />
      )}
      {detailOpen && activeDetailLiteral
        ? createPortal(
            <EntryDetailPanel
              key={`${activeDetailLiteral}-${preferredJyutping ?? ''}`}
              literal={activeDetailLiteral}
              model={detailModel?.literal === activeDetailLiteral ? detailModel : null}
              loading={!detailModel}
              relationsLoading={detailRelationsLoading}
              lang={uiLang}
              preferredJyutping={preferredJyutping}
              onClose={closeEntryDetail}
              onRelationPick={handleRelationPick}
            />,
            document.body,
          )
        : null}
    </>
  );
}

export default App;
