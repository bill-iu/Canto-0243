/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useDB, useSearch } from './hooks/useDB.tsx';
import { getActiveDbBackendMode } from './db/init';
import { useQueryExplain } from './hooks/useQueryExplain.tsx';
import { useDebouncedSearchQuery } from './hooks/useDebouncedSearchQuery.ts';
import { useEntryDetailInset } from './hooks/useEntryDetailInset.ts';
import { ResultList, type EntryPickPayload } from './result-list';
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
import { SynResultList, synResultsStats } from './syn-result-list';
import {
  AnchorResultList,
  anchorResultsStats,
  hasAnchorResultLayout,
} from './anchor-result-list';
import { formatEmptySearchMessage } from './empty-search-message';
import { isRelationSyntaxQuery } from './db/query-engine';
import { GuideView } from './guide-view';
import { AboutView } from './about-view';
import { ModeMenu } from './mode-menu';
import type { GuideMode } from './guide-examples';
import { mergeShuffledResults, shuffleResults } from './shuffle-results';
import { ShuffleIcon } from './shuffle-icon';
import type { QueryResult } from './db/query';
import { modeMetaFor, modeRedirectHint, type UiMode } from './mode-meta';
import { parseSearchUrl } from './search-url';
import { BrandSvgDefs } from './brand-svg-defs';
import { BrandLogo, GateInkMeter } from './brand-logo';
import { ReadyGate } from './ready-gate';
import { hasPwaGateLanded } from './pwa-shell-boot';
import { usePwaInstallPrompt } from './hooks/usePwaInstallPrompt';
import { PwaInstallBanner } from './components/PwaInstallBanner';
import { QueryTabsBar } from './query-tabs/query-tabs-bar';
import { useQueryTabs, VIEW } from './query-tabs/useQueryTabs';
import { getLang, setLang, t, getTheme, setTheme } from '../../frontend/app-context.mjs';

const initialUrl =
  typeof window !== 'undefined'
    ? parseSearchUrl(window.location.search)
    : { q: '', mode: '0243' as UiMode, view: 'search' as const };

function App() {
  const lexiconVersion = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  const conn = (navigator as any).connection;
  const isLikelyMetered =
    Boolean(conn?.saveData) ||
    (typeof conn?.effectiveType === 'string' && /(^|-)2g$/.test(conn.effectiveType));

  const [mode, setMode] = useState<UiMode>(initialUrl.mode);
  const [last0243Mode, setLast0243Mode] = useState<'0243' | '02493'>(() =>
    initialUrl.mode === '02493' ? '02493' : '0243',
  );

  const {
    tabState,
    activeTab,
    tabs,
    selectTab,
    addSearchTab,
    closeTab,
    reorderTabs,
    openGuide,
    openAbout,
    goHome,
    ensureActiveSearchTab,
    patchSearchTab,
    commitActiveSearch,
    pushBrowserUrl,
    popstateFrame,
    consumePopstateFrame,
    needsInitialSearch,
    initialBootstrap,
  } = useQueryTabs({ currentMode: mode, onModeChange: setMode });

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
  const [gateOpen, setGateOpen] = useState(() => !hasPwaGateLanded());
  const [uiLang, setUiLang] = useState<'zh' | 'en'>(() => getLang() as 'zh' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(
    () => getTheme({ defaultTheme: 'dark' }) as 'light' | 'dark',
  );
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailModel, setDetailModel] = useState<EntryDetailModel | null>(null);
  const [detailRelationsLoading, setDetailRelationsLoading] = useState(false);
  const [activeDetailLiteral, setActiveDetailLiteral] = useState<string | null>(null);
  const [preferredJyutping, setPreferredJyutping] = useState<string | null>(null);
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
  const searchKey = `${searchQuery}\0${mode}`;
  const modeMeta = modeMetaFor(mode, uiLang);

  const loadSearchTabUi = useCallback(
    (tab: typeof activeTab, live: boolean) => {
      if (!tab || tab.view !== VIEW.SEARCH) return;
      syncedTabIdRef.current = null;
      hydrateSearch(tab.q || '');
      const useLive = live || initialBootstrap.forceLive;
      setUseLiveFetch(useLive);
      setResultsShuffled(false);
      if (!useLive) {
        const cached = (tab.results as QueryResult[]) || [];
        setDisplayResults(cached);
        setCachedTotal(tab.total ?? null);
        syncedTabIdRef.current = tab.id;
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
      setRedirectHint(modeRedirectHint(last0243Mode === '02493' ? 'm2' : 'm1', uiLang));
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
    if (syncedTabIdRef.current !== activeTab?.id) return;
    patchSearchTab(activeTab!.id, {
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

  const { summary: explainSummary, warning: explainWarning } = useQueryExplain(inputQuery);
  const showExplain = view === 'search' && Boolean(explainSummary || explainWarning);

  const displayHint = redirectHint || searchHint;
  const effectiveTotal = useLiveFetch ? total : cachedTotal;
  const headerPreparing = offlineStatus === 'preparing' && !gateOpen;
  const headerInkProgress = headerPreparing ? Math.max(progress / 100, 0.12) : 1;
  const headerStatusLabel =
    uiLang === 'en'
      ? `Preparing lexicon${progress > 0 ? ` ${Math.round(progress)}%` : ''}`
      : `準備詞庫${progress > 0 ? ` ${Math.round(progress)}%` : ''}`;

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
    (nextQuery?: string) => {
      const q = (nextQuery ?? inputQuery).trim();
      if (pickAnchorRef.current && pickAnchorRef.current !== q) {
        pickAnchorRef.current = null;
        pickAnchorRowsRef.current = [];
      }
      flushSearchQuery(q);
      setUseLiveFetch(true);
      setResultsShuffled(false);
      const pushed = commitActiveSearch(q, mode);
      pushBrowserUrl(tabState, !pushed);
      if (q && !isReady && !lexiconLoadStartedRef.current && offlineStatus !== 'error') {
        lexiconLoadStartedRef.current = true;
        void initialize();
      }
    },
    [inputQuery, flushSearchQuery, commitActiveSearch, mode, pushBrowserUrl, tabState, isReady, offlineStatus, initialize],
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

  const handleModeChange = (next: UiMode) => {
    if (next === '0243' || next === '02493') {
      setLast0243Mode(next);
    }
    setMode(next);
    if (view === 'guide') {
      ensureActiveSearchTab();
    }
    if (trimmedInput) {
      runCommittedSearch();
    }
  };

  const handleBackToSearch = () => {
    ensureActiveSearchTab();
  };

  const handleRunExample = (nextQuery: string, exampleMode: GuideMode) => {
    if (exampleMode === '0243' || exampleMode === '02493') {
      setLast0243Mode(exampleMode);
    }
    setMode(exampleMode);
    ensureActiveSearchTab();
    runCommittedSearch(nextQuery);
  };

  const handleShuffle = () => {
    setDisplayResults(shuffleResults(results));
    setResultsShuffled(true);
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

  const synLayout = mode === 'synonym';
  const anchorLayout = !synLayout && hasAnchorResultLayout(displayResults);

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
    [mode, detailOpen, activeDetailLiteral, closeEntryDetail, beginPickSearch],
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
        onRetry={handleRetryOfflineReady}
        onOpenChange={setGateOpen}
        theme={uiTheme}
      />
      <div className={`app-shell${shellGated ? ' is-gated' : ' is-revealing'}${shouldShowInstallBanner ? ' has-install-banner' : ''}`}>
        <header className="app-header">
          <div className="app-bar">
            <button className="brand" type="button" aria-label={uiLang === 'zh' ? '返回搜尋首頁' : 'Back to search home'} onClick={handleHome}>
              <BrandLogo
                variant={headerPreparing ? 'gate' : 'header'}
                inkProgress={headerInkProgress}
                theme={uiTheme}
              />
            </button>
            {headerPreparing && (
              <div className="header-load-status" role="status" aria-live="polite" aria-busy="true">
                <GateInkMeter inkProgress={headerInkProgress} theme={uiTheme} />
                <span>{headerStatusLabel}</span>
              </div>
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
              className={`search-view${detailOpen ? ' has-entry-detail' : ''}`}
              aria-labelledby="searchTitle"
            >
              <div className="search-view__main" onClick={handleSearchMainClick}>
              <div className="hero">
                <p className="eyebrow">Cantonese Lyrics Writing Workbench</p>
                <h1 id="searchTitle">{uiLang === 'en' ? 'ONE-RUN-RHYME' : 'ONE·搵·韻'}</h1>
                <p>{uiLang === 'en' ? 'Meter / sound match / rhyme / near-antonyms — find in one step.' : '格律／協音／押韻／近反義，一步搵到。'}</p>
              </div>

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
                  <div className="search-input-wrap">
                    <input
                      id="searchInput"
                      type="search"
                      value={inputQuery}
                      onChange={(e) => handleSearchInput(e.target.value)}
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
                      disabled={!canSearch || !trimmedInput}
                    >
                      {uiLang === 'en' ? 'Search' : '搜尋'}
                    </button>
                  </div>
                </div>
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
                        onPick={(word) => runCommittedSearch(word)}
                      />
                    ) : anchorLayout ? (
                      <AnchorResultList
                        results={displayResults}
                        activeLiteral={activeDetailLiteral}
                        lang={uiLang}
                        onPick={handleEntryPick}
                      />
                    ) : (
                      <ResultList
                        results={displayResults}
                        activeLiteral={activeDetailLiteral}
                        lang={uiLang}
                        onPick={handleEntryPick}
                      />
                    )}
                    {useLiveFetch && hasMore && (
                      <button
                        type="button"
                        className="load-more"
                        onClick={() => void loadMore()}
                        disabled={loadingMore || searchLoading}
                      >
                        {loadingMore ? '載入中…' : '載入更多'}
                      </button>
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
              </div>
              </div>
              {detailOpen && activeDetailLiteral ? (
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
                />
              ) : null}
            </section>
          )}
        </main>

        <footer className="app-footer">
          <p>Canto-0243 PWA</p>
          <p>
            離線粵語填詞查詢工具 · 詞庫版本：{lexiconVersion}
            {isReady && getActiveDbBackendMode() === 'opfs-vfs' ? ' · OPFS' : ''}
          </p>
        </footer>
      </div>

      {shouldShowInstallBanner && (
        <PwaInstallBanner
          hasNativePrompt={hasNativePrompt}
          onTrigger={trigger}
          onDismiss={() => setInstallDismissed(true)}
        />
      )}
    </>
  );
}

export default App;
