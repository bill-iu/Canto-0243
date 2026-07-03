/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect, useMemo, useRef } from 'react';
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
import { parseSearchUrl, replaceAppUrl, type AppView } from './search-url';
import { BrandSvgDefs } from './brand-svg-defs';
import { BrandLogo } from './brand-logo';
import { ReadyGate } from './ready-gate';

const initialUrl =
  typeof window !== 'undefined'
    ? parseSearchUrl(window.location.search)
    : { q: '', mode: '0243' as UiMode, view: 'search' as AppView };

function App() {
  const lexiconVersion = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  const conn = (navigator as any).connection;
  const isLikelyMetered =
    Boolean(conn?.saveData) ||
    (typeof conn?.effectiveType === 'string' && /(^|-)2g$/.test(conn.effectiveType));

  const {
    inputQuery,
    searchQuery,
    setInputQueryDebounced,
    flushSearchQuery,
    hydrateSearch,
  } = useDebouncedSearchQuery(initialUrl.q);

  const [view, setView] = useState<AppView>(initialUrl.view);
  const [mode, setMode] = useState<UiMode>(initialUrl.mode);
  const [last0243Mode, setLast0243Mode] = useState<'0243' | '02493'>(() =>
    initialUrl.mode === '02493' ? '02493' : '0243',
  );
  const [redirectHint, setRedirectHint] = useState<string | null>(null);
  const [showStats, setShowStats] = useState(false);
  const [displayResults, setDisplayResults] = useState<QueryResult[]>([]);
  const [resultsShuffled, setResultsShuffled] = useState(false);
  const [gateOpen, setGateOpen] = useState(true);
  const searchKeyRef = useRef('');

  const trimmedInput = inputQuery.trim();
  const relationSyntax = trimmedInput ? isRelationSyntaxQuery(trimmedInput) : false;
  const searchKey = `${searchQuery}\0${mode}`;
  const modeMeta = modeMetaFor(mode);

  // ponytail: 介面轉接 — match desktop maybeModeRedirectForRelationSyntax
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

  const {
    results,
    total,
    hint: searchHint,
    loading: searchLoading,
    loadingMore,
    error: searchError,
    hasMore,
    loadMore,
  } = useSearch(searchQuery, mode, { fallback_0243_mode: last0243Mode });

  useEffect(() => {
    if (searchKeyRef.current !== searchKey) {
      searchKeyRef.current = searchKey;
      setResultsShuffled(false);
    }
  }, [searchKey]);

  useEffect(() => {
    if (!resultsShuffled) {
      setDisplayResults(results);
      return;
    }
    setDisplayResults((prev) => mergeShuffledResults(prev, results));
  }, [results, resultsShuffled]);

  const { summary: explainSummary, warning: explainWarning } = useQueryExplain(inputQuery);
  const showExplain = view === 'search' && Boolean(explainSummary || explainWarning);

  const displayHint = redirectHint || searchHint;

  useEffect(() => {
    if (isOnline || isDbCached) {
      initialize();
    }
  }, [initialize, isOnline, isDbCached]);

  useEffect(() => {
    replaceAppUrl({ q: searchQuery, mode, view });
  }, [searchQuery, mode, view]);

  const [stats, setStats] = useState<{ wordCount: number; tableCount: number } | null>(null);
  useEffect(() => {
    if (isReady && showStats && !stats) {
      getStats().then(setStats).catch(console.error);
    }
  }, [isReady, showStats, stats, getStats]);

  const handlePickResult = (nextQuery: string) => {
    flushSearchQuery(nextQuery);
  };

  const handleModeChange = (next: UiMode) => {
    if (next === '0243' || next === '02493') {
      setLast0243Mode(next);
    }
    setMode(next);
    if (trimmedInput) {
      flushSearchQuery();
    }
  };

  const handleGuideModePick = (next: UiMode) => {
    handleModeChange(next);
    setView('search');
  };

  const handleBackToSearch = () => {
    setView('search');
  };

  const handleRunExample = (nextQuery: string, exampleMode: GuideMode) => {
    if (exampleMode === '0243' || exampleMode === '02493') {
      setLast0243Mode(exampleMode);
    }
    setMode(exampleMode);
    hydrateSearch(nextQuery);
    setResultsShuffled(false);
    setView('search');
  };

  const handleShuffle = () => {
    setDisplayResults(shuffleResults(results));
    setResultsShuffled(true);
  };

  const handleSubmit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    flushSearchQuery();
  };

  const synLayout = mode === 'synonym';
  const anchorLayout = !synLayout && hasAnchorResultLayout(displayResults);
  const statsSuffix = `（${modeMeta.statsLabel}）`;

  const resultsLabel = useMemo(() => {
    if (synLayout && displayResults.length > 0) {
      return `${synResultsStats(displayResults)}${statsSuffix}`;
    }
    if (anchorLayout && displayResults.length > 0) {
      return `${anchorResultsStats(displayResults, total)}${statsSuffix}`;
    }
    if (total != null && total > displayResults.length) {
      return `已載入 ${displayResults.length} / ${total} 個結果${statsSuffix}`;
    }
    if (displayResults.length > 0) {
      return `${displayResults.length} 個結果${statsSuffix}`;
    }
    return '';
  }, [synLayout, anchorLayout, displayResults, total, statsSuffix]);

  const emptyMessage = useMemo(() => {
    if (!searchQuery || searchLoading || results.length > 0 || offlineStatus !== 'ready') {
      return null;
    }
    return formatEmptySearchMessage(searchQuery, displayHint, mode);
  }, [searchQuery, searchLoading, results.length, offlineStatus, displayHint, mode]);

  const toggleStats = () => {
    setShowStats(!showStats);
  };

  const canShuffle = view === 'search' && displayResults.length > 0 && !searchLoading;
  const canSearch = isReady && !gateOpen;

  const handleHome = () => {
    setView('search');
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
      />
      <div className={`app-shell${gateOpen ? ' is-gated' : ' is-revealing'}`}>
        <header className="app-header">
          <div className="app-bar">
            <button className="brand" type="button" aria-label="返回搜尋首頁" onClick={handleHome}>
              <BrandLogo />
            </button>
            <ModeMenu
              mode={mode}
              disabled={!isReady || gateOpen}
              onModeChange={handleModeChange}
              onOpenGuide={() => setView('guide')}
              onOpenAbout={() => setView('about')}
            />
          </div>
        </header>

        <main className="main-wrap">
          {view === 'guide' ? (
            <GuideView
              currentMode={mode}
              onPick={handleRunExample}
              onModePick={handleGuideModePick}
            />
          ) : view === 'about' ? (
            <AboutView lexiconVersion={lexiconVersion} onBack={handleBackToSearch} />
          ) : (
            <section className="search-view" aria-labelledby="searchTitle">
              <div className="hero">
                <p className="eyebrow">Cantonese Lyrics Writing Workbench</p>
                <h1 id="searchTitle">ONE·搵·韻</h1>
                <p>格律／協音／押韻／近反義，一步搵到。</p>
              </div>

              <form onSubmit={handleSubmit} className="search-panel" role="search">
                <div className="field-label-row">
                  <label className="field-label" htmlFor="searchInput">
                    搜尋內容
                  </label>
                  <span className="mode-readout" aria-live="polite">
                    目前模式：{modeMeta.readout}
                  </span>
                </div>
                <div className="search-row">
                  <div className="search-input-wrap">
                    <input
                      id="searchInput"
                      type="search"
                      value={inputQuery}
                      onChange={(e) => setInputQueryDebounced(e.target.value)}
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
                      aria-label="隨機打亂結果"
                      title="隨機打亂結果"
                    >
                      <ShuffleIcon />
                    </button>
                    <button
                      type="submit"
                      className="primary-button"
                      disabled={!canSearch || !trimmedInput}
                    >
                      搜尋
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
                {searchLoading && <p className="loading">搜尋中…</p>}
                {searchError && <p className="error">錯誤: {searchError.message}</p>}

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
                    {hasMore && (
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
    </>
  );
}

export default App;
