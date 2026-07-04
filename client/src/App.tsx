/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useDB, useSearch } from './hooks/useDB.tsx';
import { useQueryExplain } from './hooks/useQueryExplain.tsx';
import { useDebouncedSearchQuery } from './hooks/useDebouncedSearchQuery.ts';
import { ResultList } from './result-list';
import { SynResultList, synResultsStats } from './syn-result-list';
import {
  AnchorResultList,
  anchorResultsStats,
  hasAnchorResultLayout,
} from './anchor-result-list';
import { formatEmptySearchMessage } from './empty-search-message';
import { isRelationSyntaxQuery, modeRedirectHint } from './db/query-engine';
import { GuideView } from './guide-view';
import { AboutView } from './about-view';
import { ModeMenu } from './mode-menu';
import type { GuideMode } from './guide-examples';
import { mergeShuffledResults, shuffleResults } from './shuffle-results';
import { ShuffleIcon } from './shuffle-icon';
import type { QueryResult } from './db/query';
import { modeMetaFor, type UiMode } from './mode-meta';
import { parseSearchUrl } from './search-url';
import { BrandSvgDefs } from './brand-svg-defs';
import { BrandLogo } from './brand-logo';
import { ReadyGate } from './ready-gate';
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
  const [showStats, setShowStats] = useState(false);
  const [displayResults, setDisplayResults] = useState<QueryResult[]>([]);
  const [cachedTotal, setCachedTotal] = useState<number | null>(null);
  const [resultsShuffled, setResultsShuffled] = useState(false);
  const [gateOpen, setGateOpen] = useState(true);
  const [uiLang, setUiLang] = useState<'zh' | 'en'>(() => getLang() as 'zh' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(() => getTheme() as 'light' | 'dark');
  const searchKeyRef = useRef('');
  const activeTabIdRef = useRef<number | null>(null);
  const syncedTabIdRef = useRef<number | null>(null);
  const initialSearchDoneRef = useRef(false);

  const trimmedInput = inputQuery.trim();
  const relationSyntax = trimmedInput ? isRelationSyntaxQuery(trimmedInput) : false;
  const searchKey = `${searchQuery}\0${mode}`;
  const modeMeta = modeMetaFor(mode);

  const loadSearchTabUi = useCallback(
    (tab: typeof activeTab, live: boolean) => {
      if (!tab || tab.view !== VIEW.SEARCH) return;
      syncedTabIdRef.current = null;
      hydrateSearch(tab.q || '');
      setUseLiveFetch(live);
      setResultsShuffled(false);
      if (!live) {
        const cached = (tab.results as QueryResult[]) || [];
        setDisplayResults(cached);
        setCachedTotal(tab.total ?? null);
        syncedTabIdRef.current = tab.id;
      }
    },
    [hydrateSearch],
  );

  useEffect(() => {
    if (!activeTab) return;
    if (activeTabIdRef.current === activeTab.id) return;
    activeTabIdRef.current = activeTab.id;
    if (activeTab.view === VIEW.SEARCH) {
      const hasCache = ((activeTab.results as QueryResult[]) || []).length > 0;
      loadSearchTabUi(activeTab, !hasCache);
    } else {
      syncedTabIdRef.current = activeTab.id;
    }
  }, [activeTab, loadSearchTabUi]);

  useEffect(() => {
    if (!trimmedInput) {
      setRedirectHint(null);
      return;
    }
    if (relationSyntax) {
      setRedirectHint(modeRedirectHint(last0243Mode === '02493' ? 'm2' : 'm1'));
      if (mode === 'synonym') {
        setMode(last0243Mode);
      }
      return;
    }
    setRedirectHint(null);
  }, [trimmedInput, relationSyntax, mode, last0243Mode]);

  const {
    isReady,
    offlineStatus,
    isOnline,
    isDbCached,
    progress,
    error: dbError,
    initialize,
    retryOfflineReady,
    getStats,
  } = useDB();

  const { hasNativePrompt, trigger } = usePwaInstallPrompt();

  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as any).standalone === true;

  // Strengthened D for hybrid A+D: better detection of cold PWA launch from home screen (iOS specific for airplane cold start)
  // Use navigation type + no referrer + no landed key to detect fresh icon tap
  const navEntry = window.performance?.getEntriesByType?.('navigation')?.[0] as PerformanceNavigationTiming | undefined;
  const isColdLaunch = isStandalone && 
    (navEntry?.type === 'navigate' || !document.referrer) &&
    !sessionStorage.getItem(LANDING_SESSION_KEY);
  const isPwaLaunch = isStandalone;
  const LANDING_SESSION_KEY = 'canto-pwa-gate-landed';
  const isColdPwaOfflineLaunch = isColdLaunch && !isOnline;

  const [installDismissed, setInstallDismissed] = useState(
    () => !!sessionStorage.getItem('canto-pwa-install-dismissed')
  );

  const shouldShowInstallBanner =
    !gateOpen && !isStandalone && !installDismissed;

  // For cold PWA offline launch, force show the main shell immediately (D strengthening)
  // so user doesn't get stuck on gate or Safari error page
  if (isColdPwaOfflineLaunch) {
    // Immediately mark as "landed" and force reveal
    if (!sessionStorage.getItem(LANDING_SESSION_KEY)) {
      sessionStorage.setItem(LANDING_SESSION_KEY, '1');
    }
    // Also force gate to be considered open=false for reveal
  }

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
    loadingMore,
    error: searchError,
    hasMore,
    loadMore,
  } = useSearch(useLiveFetch ? searchQuery : '', mode, { fallback_0243_mode: last0243Mode });

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
    if (!resultsShuffled) {
      setDisplayResults(results);
      return;
    }
    setDisplayResults((prev) => mergeShuffledResults(prev, results));
  }, [results, resultsShuffled, useLiveFetch]);

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
    if (initialSearchDoneRef.current || !needsInitialSearch || !isReady || gateOpen) return;
    initialSearchDoneRef.current = true;
    setUseLiveFetch(true);
    hydrateSearch(activeSearchTab?.q || '');
    flushSearchQuery(activeSearchTab?.q || '');
  }, [
    needsInitialSearch,
    isReady,
    gateOpen,
    activeSearchTab?.q,
    hydrateSearch,
    flushSearchQuery,
  ]);

  useEffect(() => {
    if (!popstateFrame) return;
    setMode(popstateFrame.mode);
    if (popstateFrame.q) {
      setUseLiveFetch(true);
      hydrateSearch(popstateFrame.q);
      flushSearchQuery(popstateFrame.q);
    } else {
      setUseLiveFetch(false);
      hydrateSearch('');
      setDisplayResults([]);
      setCachedTotal(null);
    }
    consumePopstateFrame();
  }, [popstateFrame, hydrateSearch, flushSearchQuery, consumePopstateFrame]);

  const { summary: explainSummary, warning: explainWarning } = useQueryExplain(inputQuery);
  const showExplain = view === 'search' && Boolean(explainSummary || explainWarning);

  const displayHint = redirectHint || searchHint;
  const effectiveTotal = useLiveFetch ? total : cachedTotal;

  useEffect(() => {
    // Hybrid A+D: for cold PWA offline launch (iOS home screen in airplane), attempt init ONLY from cache (no network)
    // This prevents any implicit network attempt that could trigger Safari error
    if (isOnline || isDbCached || isColdPwaOfflineLaunch) {
      initialize();
    }
  }, [initialize, isOnline, isDbCached, isColdPwaOfflineLaunch]);

  const [stats, setStats] = useState<{ wordCount: number; tableCount: number } | null>(null);
  useEffect(() => {
    if (isReady && showStats && !stats) {
      getStats().then(setStats).catch(console.error);
    }
  }, [isReady, showStats, stats, getStats]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
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
  }, [saveLeavingSearchTab, addSearchTab, closeTab, tabState.activeId]);

  const runCommittedSearch = useCallback(
    (nextQuery?: string) => {
      const q = (nextQuery ?? inputQuery).trim();
      flushSearchQuery(q);
      setUseLiveFetch(true);
      setResultsShuffled(false);
      const pushed = commitActiveSearch(q, mode);
      pushBrowserUrl(tabState, !pushed);
    },
    [inputQuery, flushSearchQuery, commitActiveSearch, mode, pushBrowserUrl, tabState],
  );

  const handlePickResult = (nextQuery: string) => {
    runCommittedSearch(nextQuery);
  };

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

  const toggleStats = () => {
    setShowStats(!showStats);
  };

  const canShuffle = view === 'search' && displayResults.length > 0 && !searchLoading;
  const canSearch = isReady && !gateOpen;

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
        onRetry={retryOfflineReady}
        onOpenChange={setGateOpen}
        theme={uiTheme}
      />
      <div className={`app-shell${(gateOpen && !isColdPwaOfflineLaunch) ? ' is-gated' : ' is-revealing'}${shouldShowInstallBanner ? ' has-install-banner' : ''}`}>
        <header className="app-header">
          <div className="app-bar">
            <button className="brand" type="button" aria-label={uiLang === 'zh' ? '返回搜尋首頁' : 'Back to search home'} onClick={handleHome}>
              <BrandLogo theme={uiTheme} />
            </button>
            <ModeMenu
              mode={mode}
              disabled={!isReady || gateOpen}
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
            onSelect={handleSelectTab}
            onClose={handleCloseTab}
            onAdd={handleAddTab}
            onReorder={handleReorderTabs}
          />
        </header>

        <main className="main-wrap">
          {view === 'guide' ? (
            <GuideView onPick={handleRunExample} />
          ) : view === 'about' ? (
            <AboutView lexiconVersion={lexiconVersion} onBack={handleBackToSearch} />
          ) : (
            <section className="search-view" aria-labelledby="searchTitle">
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
                      disabled={gateOpen || offlineStatus === 'preparing'}
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

              <div style={{ textAlign: 'center' }}>
                <button type="button" onClick={toggleStats} className="stats-toggle">
                  {showStats ? '隱藏統計' : '顯示資料庫統計'}
                </button>
              </div>

              {showStats && stats && (
                <div className="db-stats">
                  <p>詞條數量: {stats.wordCount.toLocaleString()}</p>
                  <p>資料表數量: {stats.tableCount}</p>
                </div>
              )}

              <div className="search-results">
                {displayHint && displayResults.length > 0 && (
                  <p className="search-hint">{displayHint}</p>
                )}
                {useLiveFetch && searchLoading && <p className="loading">{uiLang === 'en' ? 'Searching…' : '搜尋中…'}</p>}
                {useLiveFetch && searchError && (
                  <p className="error">錯誤: {searchError.message}</p>
                )}

                {displayResults.length > 0 && (
                  <div className="results-list">
                    {resultsLabel ? <p className="results-count">{resultsLabel}</p> : null}
                    {synLayout ? (
                      <SynResultList results={displayResults} onPick={handlePickResult} />
                    ) : anchorLayout ? (
                      <AnchorResultList results={displayResults} onPick={handlePickResult} />
                    ) : (
                      <ResultList results={displayResults} onPick={handlePickResult} />
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
            </section>
          )}
        </main>

        <footer className="app-footer">
          <p>Canto-0243 PWA</p>
          <p>
            離線粵語填詞查詢工具 · 詞庫版本：{lexiconVersion}
            {(import.meta as ImportMeta).env?.VITE_DB_BACKEND === 'opfs' ? ' · OPFS' : ''}
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
