/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { lazy, Suspense, useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useDB, useSearch } from './hooks/useDB.ts';
import { getActiveDbBackendMode } from './db/init';
import { useQueryExplain } from './hooks/useQueryExplain.tsx';
import { useDebouncedSearchQuery } from './hooks/useDebouncedSearchQuery.ts';
import { useEntryDetailInset } from './hooks/useEntryDetailInset.ts';
import { ResultList } from './result-list';
import { mergedResultCount, resultsShowReadingBadge, type EntryPickPayload } from './result-list-logic.ts';
import { formatStandardResultCountLabel } from '../../shared/result-stats.mjs';
import { PutInWorkbenchModal } from './workbench/PutInWorkbenchModal.tsx';
import {
  WorkbenchBridgeError,
  consumeNavigate,
  consumeOpenSearch,
  hasWorkbenchDraft,
  readWorkbenchSelectionWidth,
  readWorkbenchSurfacePreview,
  writeIngest,
} from './workbench/workbench-bridge.ts';
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
} from '../../shared/entry-detail-core.mjs';
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
import { planCommitSearch } from './db/query/search-session.ts';
import { GuideQuick } from './guide-quick';
import { ModeMenu } from './mode-menu';
import type { GuideMode } from './guide-examples';
import { mergeShuffledResults, shuffleResults } from './shuffle-results';
import { ShuffleIcon } from './shuffle-icon';
import type { QueryResult } from './db/query';
import {
  last0243UiToUrlMode,
  getModeMeta,
  modeMetaFor,
  uiModeToUrlMode,
  urlModeToUiMode,
  type PingzeSubMode,
  type Last0243SearchMode,
  type UiMode,
} from './mode-meta';
import { parseSearchUrl } from './search-url';
import { profileToUiMode, searchFamilyForUiMode, uiModeToProfile } from '../../contracts/search-mode-manifest.mjs';
import { BrandSvgDefs } from './brand-svg-defs';
import { BrandLogo } from './brand-logo';
import { HeaderHero } from './header-hero.tsx';
import { workbenchPageHref } from './app-page.ts';
import { ReadyGate } from './ready-gate';
import { hasPwaGateLanded } from './pwa-shell-boot';
import { usePwaInstallPrompt } from './hooks/usePwaInstallPrompt';
import { PwaInstallBanner } from './components/PwaInstallBanner';
import {
  PortableUpdateBanner,
  type PortableUpdateInfo,
} from './components/PortableUpdateBanner';
import { TailPreloadBadge } from './components/TailPreloadBadge';
import { HostTabsBar } from '@host-tabs-bar';
import { useQueryTabs, VIEW } from './query-tabs/useQueryTabs';
import { getLang, setLang, getTheme, setTheme, SEARCH_RING_BLUR_MS, readLexiconVersionMeta } from '../../shared/app-context.mjs';
import { getAppShellCopy } from '../../shared/app-shell-i18n.mjs';
import { isCorrectionsSearchCommand } from '@shared/query-tabs';
import { isPortableHost } from './host-mode';
import { useEntrySize } from './entry-size';
import { exitPortable } from './portable-exit';
import { PosFilterControl } from './pos/PosFilterControl.tsx';
import {
  filterByProjectPos,
  isPosFilterActive,
  normalizePosFilter,
  type PosFilterState,
} from './pos/filter.ts';

const WorkbenchPage = lazy(() =>
  import('./workbench/WorkbenchPage.tsx').then(({ WorkbenchPage: Page }) => ({ default: Page })),
);
const GuideView = lazy(() =>
  import('./guide-view').then(({ GuideView: View }) => ({ default: View })),
);
const AboutView = lazy(() =>
  import('./about-view').then(({ AboutView: View }) => ({ default: View })),
);
const RelationView = lazy(() =>
  import('./views/relation-view').then(({ RelationView: View }) => ({ default: View })),
);
const CorrectionsView = lazy(() =>
  import('./views/corrections-view').then(({ CorrectionsView: View }) => ({ default: View })),
);
const EntryDetailPanel = lazy(() =>
  import('./entry-detail/EntryDetailPanel').then(({ EntryDetailPanel: Panel }) => ({ default: Panel })),
);

const initialUrl =
  typeof window !== 'undefined'
    ? parseSearchUrl(window.location.search)
    : { q: '', mode: '0243' as UiMode, pzmode: 'm1' as PingzeSubMode, view: 'search' as const };

function App() {
  const lexiconVersion =
    (isPortableHost() ? readLexiconVersionMeta() : null) ||
    (import.meta as any).env?.VITE_LEXICON_VERSION ||
    'dev';
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
    reorderTabsByIdList,
    openGuide,
    openAbout,
    openWorkbench,
    openSearchTabForLiteral,
    openRelation,
    openCorrections,
    patchActiveRelation,
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
    activeTab?.view === VIEW.WORKBENCH
      ? 'workbench'
      : activeTab?.view === VIEW.GUIDE
      ? 'guide'
      : activeTab?.view === VIEW.ABOUT
        ? 'about'
        : activeTab?.view === VIEW.RELATION
          ? 'relation'
          : activeTab?.view === VIEW.CORRECTIONS
            ? 'corrections'
            : 'search';

  const {
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    setInputQueryLive,
    flushSearchQuery,
    hydrateSearch,
  } = useDebouncedSearchQuery(activeSearchTab?.q ?? '');

  const [useLiveFetch, setUseLiveFetch] = useState(true);
  const [redirectHint, setRedirectHint] = useState<string | null>(null);
  const [displayResults, setDisplayResults] = useState<QueryResult[]>([]);
  const [posFilter, setPosFilter] = useState<PosFilterState>(() =>
    normalizePosFilter(activeSearchTab?.posFilter as Partial<PosFilterState> | undefined),
  );
  const [cachedTotal, setCachedTotal] = useState<number | null>(null);
  const [resultsShuffled, setResultsShuffled] = useState(false);
  const [shuffleGeneration, setShuffleGeneration] = useState(0);
  const [gateOpen, setGateOpen] = useState(() => !hasPwaGateLanded());
  const [warmupBadgeClear, setWarmupBadgeClear] = useState(false);
  const [uiLang, setUiLang] = useState<'zh' | 'zh-Hans' | 'en'>(() => getLang() as 'zh' | 'zh-Hans' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(
    () => getTheme({ defaultTheme: 'dark' }) as 'light' | 'dark',
  );
  const [entrySize, setEntrySize] = useEntrySize();
  const [detailOpen, setDetailOpen] = useState(false);
  const [putWorkbenchLiteral, setPutWorkbenchLiteral] = useState<string | null>(null);
  const [detailModel, setDetailModel] = useState<EntryDetailModel | null>(null);
  const [detailRelationsLoading, setDetailRelationsLoading] = useState(false);
  const [activeDetailLiteral, setActiveDetailLiteral] = useState<string | null>(null);
  const [preferredJyutping, setPreferredJyutping] = useState<string | null>(null);
  const [searchRingClass, setSearchRingClass] = useState('');
  const searchRingBlurTimerRef = useRef<number | null>(null);
  const detailLoadGenRef = useRef(0);
  const detailByTabRef = useRef(new Map<number, {
    open: boolean;
    literal: string | null;
    jyutping: string | null;
  }>());
  const lastPickReadingsRef = useRef<EntryPickPayload['readings']>(undefined);
  const pickAnchorRef = useRef<string | null>(null);
  const pickAnchorRowsRef = useRef<QueryResult[]>([]);
  const scrollTopByTabRef = useRef(new Map<number, number>());

  useEntryDetailInset(detailOpen);
  const searchKeyRef = useRef('');
  const activeTabIdRef = useRef<number | null>(null);
  const syncedTabIdRef = useRef<number | null>(null);
  const initialSearchDoneRef = useRef(false);
  const lexiconLoadStartedRef = useRef(false);

  const trimmedInput = inputQuery.trim();
  const searchKey = `${searchQuery}\0${mode}\0${pzMode}`;
  const modeMeta = modeMetaFor(mode, uiLang);
  const appCopy = getAppShellCopy(uiLang);

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
      setPosFilter(normalizePosFilter(tab.posFilter as Partial<PosFilterState> | undefined));
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
    const commit = planCommitSearch({
      q: trimmedInput,
      mode: uiModeToUrlMode(mode),
      last0243Mode: last0243UiToUrlMode(last0243Mode),
      pzmode: pzMode,
      lang: uiLang,
    });
    if (commit.redirectHint) {
      setRedirectHint(commit.redirectHint);
      if (mode === 'synonym' && commit.mode !== 'syn') {
        setMode(urlModeToUiMode(commit.mode));
      }
      return;
    }
    setRedirectHint(null);
  }, [trimmedInput, mode, last0243Mode, pzMode, uiLang]);

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

  const [portableUpdate, setPortableUpdate] = useState<PortableUpdateInfo | null>(null);

  useEffect(() => {
    if (!isPortableHost()) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/portable-update');
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as PortableUpdateInfo & { skipped?: boolean };
        if (!cancelled && data.available && !data.skipped) {
          setPortableUpdate(data);
        }
      } catch {
        /* fail-open */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const dismissPortableUpdate = useCallback(async () => {
    setPortableUpdate(null);
    try {
      await fetch('/portable-update/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
    } catch {
      /* ignore */
    }
  }, []);

  // Ready → shell interactive immediately (CONTEXT 就緒閘解鎖). gateOpen only tracks overlay visibility.
  const shellGated = offlineStatus !== 'ready';

  // Portable is a local desktop host — never show PWA install chrome
  const shouldShowInstallBanner =
    !isPortableHost() && !shellGated && !isStandalone && !installDismissed;
  const shouldShowPortableUpdate =
    isPortableHost() && !!portableUpdate?.available && !shellGated;

  // Apply theme + lang (shared with vanilla via app-context)
  useEffect(() => {
    setTheme(uiTheme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', uiTheme === 'dark' ? '#1C1917' : '#DFD2C2');
  }, [uiTheme]);

  useEffect(() => {
    setLang(uiLang);
    document.documentElement.lang = uiLang === 'zh' ? 'zh-Hant' : uiLang === 'zh-Hans' ? 'zh-Hans' : 'en';
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
  } = useSearch(useLiveFetch && view === 'search' ? searchQuery : '', mode, {
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
      posFilter,
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
    posFilter,
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
    if (isReady || offlineStatus === 'failed') return;
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
  const showExplain = Boolean(explainSummary || explainWarning);
  const searchFamily = searchFamilyForUiMode(mode);

  const displayHint = redirectHint || searchHint;
  const effectiveTotal = useLiveFetch ? total : cachedTotal;
  const filterActive = isPosFilterActive(posFilter);
  const filteredDisplayResults = useMemo(
    () => filterByProjectPos(displayResults, (row) => row.word, posFilter),
    [displayResults, posFilter],
  );
  const changePosFilter = useCallback((next: PosFilterState) => {
    const normalized = normalizePosFilter(next);
    setPosFilter(normalized);
    if (activeSearchTab) patchSearchTab(activeSearchTab.id, { posFilter: normalized });
  }, [activeSearchTab, patchSearchTab]);

  useEffect(() => {
    if (!filterActive || !useLiveFetch || searchLoading || loadingMore || !hasMore) return;
    if (displayResults.length > 0 && filteredDisplayResults.length < 40) void loadMore();
  }, [filterActive, useLiveFetch, searchLoading, loadingMore, hasMore, displayResults.length, filteredDisplayResults.length, loadMore]);
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

  const saveActiveDetail = useCallback(() => {
    if (activeTab?.view !== VIEW.SEARCH) return;
    detailByTabRef.current.set(activeTab.id, {
      open: detailOpen,
      literal: activeDetailLiteral,
      jyutping: preferredJyutping,
    });
  }, [activeTab, detailOpen, activeDetailLiteral, preferredJyutping]);

  useEffect(() => {
    if (activeTab?.view !== VIEW.SEARCH) {
      closeEntryDetail();
      return;
    }
    const saved = detailByTabRef.current.get(activeTab.id);
    if (!saved?.open || !saved.literal) {
      closeEntryDetail();
      return;
    }
    setDetailOpen(true);
    setActiveDetailLiteral(saved.literal);
    setPreferredJyutping(saved.jyutping);
    setDetailModel(null);
  }, [activeTab?.id, activeTab?.view, closeEntryDetail]);

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
      // ponytail: portable maintainer — `debug` opens corrections, not a search
      if (isPortableHost() && isCorrectionsSearchCommand(q)) {
        saveLeavingSearchTab();
        openCorrections();
        return;
      }
      if (pickAnchorRef.current && pickAnchorRef.current !== q) {
        pickAnchorRef.current = null;
        pickAnchorRowsRef.current = [];
      }
      flushSearchQuery(q);
      setUseLiveFetch(true);
      setResultsShuffled(false);
      commitActiveSearch(q, nextMode, nextPzMode);
      if (q && !isReady && !lexiconLoadStartedRef.current && offlineStatus !== 'failed') {
        lexiconLoadStartedRef.current = true;
        void initialize();
      }
    },
    [
      inputQuery,
      flushSearchQuery,
      commitActiveSearch,
      mode,
      pzMode,
      isReady,
      offlineStatus,
      initialize,
      saveLeavingSearchTab,
      openCorrections,
    ],
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
    if (view === 'workbench' || view === 'guide') {
      ensureActiveSearchTab();
    }
    const next = family === 'basic' ? last0243Mode : family === 'pingze' ? 'pingze' : 'synonym';
    setMode(next);
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

  const openLiveSearchTab = useCallback(
    (q: string, nextMode: UiMode = mode) => {
      saveLeavingSearchTab();
      openSearchTabWithQuery(q, nextMode, pzMode);
      setUseLiveFetch(true);
      setResultsShuffled(false);
      if (q && !isReady && !lexiconLoadStartedRef.current && offlineStatus !== 'failed') {
        lexiconLoadStartedRef.current = true;
        void initialize();
      }
    },
    [saveLeavingSearchTab, openSearchTabWithQuery, mode, pzMode, isReady, offlineStatus, initialize],
  );

  const navigateWithIngest = useCallback((literal: string, ingestMode: 'replace' | 'insert') => {
    try {
      writeIngest(sessionStorage, { literal, mode: ingestMode });
      openWorkbench();
    } catch (error) {
      window.alert(error instanceof WorkbenchBridgeError ? error.message : '無法放入句格。');
    }
  }, [openWorkbench]);

  const handlePutInWorkbench = useCallback((literal: string) => {
    const text = literal.trim();
    if (!text) return;
    if (!hasWorkbenchDraft(localStorage)) {
      navigateWithIngest(text, 'replace');
      return;
    }
    setPutWorkbenchLiteral(text);
  }, [navigateWithIngest]);

  useEffect(() => {
    const nav = consumeNavigate(sessionStorage);
    if (nav?.kind === 'mode') {
      const next = nav.family === 'basic' ? last0243Mode : nav.family === 'pingze' ? 'pingze' : 'synonym';
      setMode(next);
    } else if (nav?.kind === 'guide') {
      openGuide();
    } else if (nav?.kind === 'about') {
      openAbout();
    }

    const payload = consumeOpenSearch(sessionStorage);
    if (!payload) return;
    openLiveSearchTab(payload.literal);
    hydrateSearch(payload.literal);
  // ponytail: one-shot bridge consume on search mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleBackToSearch = () => {
    ensureActiveSearchTab();
  };

  const handleRunExample = (nextQuery: string, exampleMode: GuideMode) => {
    if (exampleMode === '0243' || exampleMode === '02493' || exampleMode === '394052') {
      setLast0243Mode(exampleMode);
    }
    setMode(exampleMode);
    // 教學例子：開新搜尋 tab，唔覆蓋當前 tab
    openLiveSearchTab(nextQuery, exampleMode as UiMode);
  };

  const handleShuffle = () => {
    setDisplayResults(shuffleResults(results));
    setResultsShuffled(true);
    setShuffleGeneration((n) => n + 1);
  };

  const handleSubmit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    // 教學／關於／維護者：送出開新搜尋 tab（同教學範例），保留原 tab；唔共用 ensureActive→commit 嘅 race
    if (view === 'guide' || view === 'about' || view === 'relation' || view === 'corrections') {
      const q = inputQuery.trim();
      if (isPortableHost() && isCorrectionsSearchCommand(q)) {
        openCorrections();
        return;
      }
      openLiveSearchTab(q);
      return;
    }
    runCommittedSearch();
  };

  const handleReorderTabs = (fromIndex: number, toIndex: number) => {
    saveLeavingSearchTab();
    reorderTabs(fromIndex, toIndex);
  };

  const handleReorderTabsByIds = (orderedIds: number[]) => {
    saveLeavingSearchTab();
    reorderTabsByIdList(orderedIds);
  };

  const handleSelectTab = (id: number) => {
    saveLeavingSearchTab();
    saveActiveDetail();
    selectTab(id);
  };

  const handleCloseTab = (id: number) => {
    saveLeavingSearchTab();
    saveActiveDetail();
    detailByTabRef.current.delete(id);
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

  const handleOpenRelation = () => {
    saveLeavingSearchTab();
    openRelation();
  };

  const handleSearchInput = (value: string) => {
    if (view !== 'search') {
      setInputQueryLive(value);
      return;
    }
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
  const anchorLayout = !synLayout && hasAnchorResultLayout(filteredDisplayResults);
  const [scrollRootEl, setScrollRootEl] = useState<HTMLDivElement | null>(null);
  const infiniteScrollRoot = scrollRootEl;

  useEffect(() => {
    const root = scrollRootEl;
    const tabId = activeSearchTab?.id;
    if (!root || tabId == null) return;
    const saved = scrollTopByTabRef.current.get(tabId) ?? 0;
    requestAnimationFrame(() => { root.scrollTop = saved; });
    const save = () => { scrollTopByTabRef.current.set(tabId, root.scrollTop); };
    root.addEventListener('scroll', save, { passive: true });
    return () => {
      save();
      root.removeEventListener('scroll', save);
    };
  }, [scrollRootEl, activeSearchTab?.id]);

  const resultItemCount = useMemo(() => {
    if (!filteredDisplayResults.length) return 0;
    if (synLayout) return synResultItemCount(filteredDisplayResults);
    if (anchorLayout) return anchorResultItemCount(filteredDisplayResults);
    return mergedResultCount(filteredDisplayResults);
  }, [filteredDisplayResults, synLayout, anchorLayout]);

  const { visibleCount, sentinelRef, showSentinel } = useInfiniteResultWindow({
    itemCount: resultItemCount,
    hasMore: Boolean(useLiveFetch && hasMore),
    loading: searchLoading,
    loadingMore,
    onLoadMore: () => void loadMore(),
    resetKey: `${searchKey}\0${shuffleGeneration}\0${JSON.stringify(posFilter)}`,
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
    if (filterActive) {
      return appCopy.filteredResults(resultItemCount, displayResults.length, statsSuffix);
    }
    if (synLayout && filteredDisplayResults.length > 0) {
      return `${synResultsStats(filteredDisplayResults)}${statsSuffix}`;
    }
    if (anchorLayout && filteredDisplayResults.length > 0) {
      return `${anchorResultsStats(filteredDisplayResults, effectiveTotal)}${statsSuffix}`;
    }
    if (!filteredDisplayResults.length || resultItemCount <= 0) return '';
    // 標準列表：有字面總數先顯示「搜到 Y」；未返 total 唔寫
    const body = formatStandardResultCountLabel(effectiveTotal);
    return body ? `${body}${statsSuffix}` : '';
  }, [
    synLayout,
    anchorLayout,
    filteredDisplayResults,
    filterActive,
    appCopy,
    displayResults.length,
    effectiveTotal,
    resultItemCount,
    statsSuffix,
  ]);

  const emptyMessage = useMemo(() => {
    if (!searchQuery || searchLoading || displayResults.length > 0 || offlineStatus !== 'ready') {
      return null;
    }
    if (!useLiveFetch) return null;
    return formatEmptySearchMessage(searchQuery, displayHint, mode as '0243' | '02493' | 'synonym');
  }, [searchQuery, searchLoading, displayResults.length, offlineStatus, displayHint, mode, useLiveFetch]);

  const filterEmpty = filterActive && displayResults.length > 0 && filteredDisplayResults.length === 0;

  const canShuffle = view === 'search' && filteredDisplayResults.length > 0 && !searchLoading;
  const showGuideQuick =
    view === 'search' &&
    !trimmedInput &&
    !searchQuery.trim() &&
    displayResults.length === 0 &&
    !searchLoading &&
    !emptyMessage;

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

  const handleBrandClick = () => {
    if (view === 'workbench') {
      const hasQuery = tabs.some(
        (t) => t.view === VIEW.SEARCH && String((t as { q?: string }).q || '').trim(),
      );
      if (hasQuery) {
        ensureActiveSearchTab();
        return;
      }
    }
    handleHome();
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
        className={`app-shell${shellGated ? ' is-gated' : ' is-revealing'}${view === 'workbench' ? ' app-shell--workbench' : ''}${shouldShowInstallBanner ? ' has-install-banner' : ''}${shouldShowPortableUpdate ? ' has-portable-update-banner' : ''}${detailOpen ? ' has-entry-detail' : ''}`}
      >
        <header className="app-header">
          <h1 id="searchTitle" className="sr-only">
            {appCopy.title}
          </h1>
          <HostTabsBar
            tabs={tabs}
            activeId={tabState.activeId}
            lang={uiLang}
            onSelect={handleSelectTab}
            onClose={handleCloseTab}
            onAdd={handleAddTab}
            onReorder={handleReorderTabs}
            onReorderByIds={handleReorderTabsByIds}
          />
          <div className={`app-bar${view === 'workbench' ? ' app-bar--workbench' : ''}`}>
            <div className="header-chrome">
              <div className="header-chrome__center">
                <button
                  className="brand"
                  type="button"
                  aria-label={appCopy.returnToSearch}
                  onClick={handleBrandClick}
                >
                  <BrandLogo variant="header" inkProgress={1} theme={uiTheme} />
                </button>
              </div>
              <div className="header-chrome__actions">
                {view !== 'workbench' ? (
                  <a
                    className="workbench-entry workbench-entry--chip"
                    href={workbenchPageHref()}
                    onClick={(e) => {
                      e.preventDefault();
                      openWorkbench();
                    }}
                  >
                    <span className="workbench-entry__icon" aria-hidden="true">
                      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                        <rect x="1.5" y="3" width="15" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" />
                        <path d="M1.5 7.5h15M7.5 7.5v7.5M12 7.5v7.5" stroke="currentColor" strokeWidth="1.5" />
                      </svg>
                    </span>
                    <span className="workbench-entry__text">
                      <span className="workbench-entry__title">
                        {appCopy.workbenchTitle}
                      </span>
                      <span className="workbench-entry__sub">
                        {appCopy.workbenchSub}
                      </span>
                    </span>
                  </a>
                ) : null}
                <ModeMenu
                  mode={mode}
                  disabled={shellGated}
                  onModeChange={handleModeChange}
                  onOpenGuide={handleOpenGuide}
                  onOpenAbout={handleOpenAbout}
                  onOpenWorkbench={view !== 'workbench' ? openWorkbench : undefined}
                  onOpenRelation={isPortableHost() ? handleOpenRelation : undefined}
                  onExitPortable={isPortableHost() ? () => void exitPortable(uiLang === 'en' ? 'en' : 'zh') : undefined}
                  theme={uiTheme}
                  lang={uiLang}
                  onThemeChange={(next) => setUiTheme(next)}
                  onLangChange={(next) => setUiLang(next)}
                  entrySize={entrySize}
                  onEntrySizeChange={setEntrySize}
                  lexiconVersion={lexiconVersion}
                  showOpfsBackend={
                    !isPortableHost() && isReady && getActiveDbBackendMode() === 'opfs-vfs'
                  }
                />
              </div>
            </div>
            {/* 寬／窄屏：grid 與 logo｜menu 同行；窄屏 tagline 縮字／極窄隱藏 */}
            <HeaderHero lang={uiLang} />
            <form
              className="header-search"
              onSubmit={handleSubmit}
              role="search"
              hidden={view === 'workbench'}
            >
              <div className="header-search__row">
                <div className="header-search__main">
                  <div className={`search-input-wrap${searchRingClass ? ` ${searchRingClass}` : ''}`}>
                    <label className="sr-only" htmlFor="searchInput">
                      {appCopy.searchLabel}
                    </label>
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
                </div>
                <div className="header-search__actions">
                  <button
                    type="submit"
                    className="primary-button header-search__submit"
                    disabled={shellGated}
                  >
                    {appCopy.searchButton}
                  </button>
                  <button
                    type="button"
                    className="icon-button header-search__shuffle"
                    onClick={handleShuffle}
                    disabled={!canShuffle}
                    aria-label={appCopy.shuffleResults}
                    title={appCopy.shuffleResults}
                  >
                    <ShuffleIcon />
                  </button>
                </div>
              </div>
              <div className="header-search__meta">
                <PosFilterControl value={posFilter} onChange={changePosFilter} lang={uiLang} disabled={shellGated} />
                {searchFamily !== 'synonym' ? (
                  <div
                    className="pingze-submodes"
                    role="group"
                    aria-label={appCopy.toneProfile}
                  >
                    {(['m1', 'm2', 'm3'] as PingzeSubMode[]).map((subMode) => (
                      <button
                        key={subMode}
                        type="button"
                        className={`pingze-submode${(mode === 'pingze' ? pzMode : uiModeToProfile(mode)) === subMode ? ' is-active' : ''}`}
                        aria-pressed={(mode === 'pingze' ? pzMode : uiModeToProfile(mode)) === subMode}
                        title={getModeMeta(subMode, uiLang).title}
                        disabled={shellGated}
                        onClick={() => handleProfileChange(subMode)}
                      >
                        <span className="profile-pill__wide">{getModeMeta(subMode, uiLang).title}</span>
                        <span className="profile-pill__narrow">
                          {subMode === 'm1' ? '四聲' : subMode === 'm2' ? '五聲' : '六聲'}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : null}
                {showExplain ? (
                  <p className="query-explain" aria-live="polite">
                    {explainSummary ? (
                      <span className="query-explain__summary">{explainSummary}</span>
                    ) : null}
                    {explainWarning ? (
                      <span className="query-explain__warning">{explainWarning}</span>
                    ) : null}
                  </p>
                ) : null}
                {mountWarmupBadge ? (
                  <TailPreloadBadge
                    tailProgress={tailProgress}
                    startupComplete={startupComplete}
                    theme={uiTheme}
                    lang={uiLang}
                    onDismiss={handleWarmupBadgeDismiss}
                  />
                ) : null}
              </div>
            </form>
          </div>
        </header>

        <main className="main-wrap">
          {view === 'workbench' ? (
            <Suspense fallback={null}>
              <WorkbenchPage
                embedded
                active
                lang={uiLang}
                theme={uiTheme}
                onOpenSearchLiteral={(literal) => openSearchTabForLiteral(literal, mode, pzMode)}
              />
            </Suspense>
          ) : null}
          {view !== 'workbench' ? (
            <Suspense fallback={null}>
              {view === 'guide' ? (
                <GuideView lang={uiLang} onPick={handleRunExample} />
              ) : view === 'about' ? (
                <AboutView lang={uiLang} lexiconVersion={lexiconVersion} onBack={handleBackToSearch} />
              ) : view === 'relation' && isPortableHost() ? (
                <RelationView
                  lang={uiLang}
                  initial={activeTab?.relation}
                  onFormChange={(next) => patchActiveRelation(next as unknown as Record<string, string>)}
                />
              ) : view === 'corrections' && isPortableHost() ? (
                <CorrectionsView lang={uiLang} prefetchChar={activeTab?.prefetchChar} />
              ) : (
                <section
                  className={`search-view${detailOpen ? ' has-entry-detail' : ''}${showGuideQuick ? ' is-empty-landing' : ''}`}
                  aria-labelledby="searchTitle"
                >
              <div className="search-view__main" onClick={handleSearchMainClick}>
              <div className="search-results">
                <div className="search-results-scroll" ref={setScrollRootEl}>
                  {displayHint && filteredDisplayResults.length > 0 && (
                    <p className="search-hint">{displayHint}</p>
                  )}
                  {useLiveFetch && searchLoadingVisible && (
                    <p className="loading">{appCopy.searching}</p>
                  )}
                  {useLiveFetch && searchError && (
                    <p className="error">錯誤: {searchError.message}</p>
                  )}

                  {filteredDisplayResults.length > 0 && (
                    <div className="results-list">
                      {resultsLabel ? <p className="results-count">{resultsLabel}</p> : null}
                      {synLayout ? (
                        <SynResultList
                          results={filteredDisplayResults}
                          visibleLimit={visibleCount}
                          onPick={(word) => runCommittedSearch(word)}
                        />
                      ) : anchorLayout ? (
                        <AnchorResultList
                          results={filteredDisplayResults}
                          visibleLimit={visibleCount}
                          activeLiteral={activeDetailLiteral}
                          lang={uiLang}
                          onPick={handleEntryPick}
                        />
                      ) : (
                        <ResultList
                          results={filteredDisplayResults}
                          showReadingBadge={resultsShowReadingBadge(inputQuery)}
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

                  {filterEmpty ? <div className="no-results info"><p><strong>{appCopy.noLoadedResults}</strong></p><p>{hasMore ? appCopy.loadingMore : appCopy.resetFilter}</p></div> : null}

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
            </Suspense>
          ) : null}
        </main>
      </div>

      {shouldShowInstallBanner && (
        <PwaInstallBanner
          hasNativePrompt={hasNativePrompt}
          onTrigger={trigger}
          onDismiss={() => setInstallDismissed(true)}
        />
      )}
      {shouldShowPortableUpdate && portableUpdate ? (
        <PortableUpdateBanner
          info={portableUpdate}
          lang={uiLang === 'en' ? 'en' : 'zh'}
          onDismiss={() => void dismissPortableUpdate()}
        />
      ) : null}
      {view === 'search' && detailOpen && activeDetailLiteral
        ? createPortal(
            <Suspense fallback={null}>
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
                onPutInWorkbench={handlePutInWorkbench}
              />
            </Suspense>,
            document.body,
          )
        : null}
      {putWorkbenchLiteral
        ? createPortal(
            <PutInWorkbenchModal
              literal={putWorkbenchLiteral}
              currentSurface={readWorkbenchSurfacePreview(localStorage)}
              selectionWidth={readWorkbenchSelectionWidth(localStorage)}
              onReplace={() => {
                const literal = putWorkbenchLiteral;
                setPutWorkbenchLiteral(null);
                navigateWithIngest(literal, 'replace');
              }}
              onInsert={() => {
                const literal = putWorkbenchLiteral;
                setPutWorkbenchLiteral(null);
                navigateWithIngest(literal, 'insert');
              }}
              onCancel={() => setPutWorkbenchLiteral(null)}
            />,
            document.body,
          )
        : null}
    </>
  );
}

export default App;
