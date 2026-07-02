/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect, useMemo } from 'react';
import { useDB, useSearch } from './hooks/useDB.tsx';
import { useQueryExplain } from './hooks/useQueryExplain.tsx';
import { ResultList } from './result-list';
import { SynResultList, synResultsStats } from './syn-result-list';
import { formatEmptySearchMessage } from './empty-search-message';
import { isRelationSyntaxQuery, modeRedirectHint } from './db/query-engine';
import './App.css';

type UiMode = '0243' | '02493' | 'synonym';

function App() {
  const lexiconVersion = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  const conn = (navigator as any).connection;
  const isLikelyMetered =
    Boolean(conn?.saveData) ||
    (typeof conn?.effectiveType === 'string' && /(^|-)2g$/.test(conn.effectiveType));

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<UiMode>('0243');
  const [last0243Mode, setLast0243Mode] = useState<'0243' | '02493'>('0243');
  const [redirectHint, setRedirectHint] = useState<string | null>(null);
  const [showStats, setShowStats] = useState(false);

  const trimmedQuery = query.trim();
  const relationSyntax = trimmedQuery ? isRelationSyntaxQuery(trimmedQuery) : false;

  // ponytail: 介面轉接 — match desktop maybeModeRedirectForRelationSyntax
  useEffect(() => {
    if (!trimmedQuery) {
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
  }, [trimmedQuery, relationSyntax, mode, last0243Mode]);

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
  } = useSearch(query, mode, { fallback_0243_mode: last0243Mode });

  const { summary: explainSummary, warning: explainWarning } = useQueryExplain(query);
  const showExplain = Boolean(explainSummary || explainWarning);

  const displayHint = redirectHint || searchHint;

  useEffect(() => {
    if (isOnline || isDbCached) {
      initialize();
    }
  }, [initialize, isOnline, isDbCached]);

  const [stats, setStats] = useState<{ wordCount: number; tableCount: number } | null>(null);
  useEffect(() => {
    if (isReady && showStats && !stats) {
      getStats().then(setStats).catch(console.error);
    }
  }, [isReady, showStats, stats, getStats]);

  const handlePickResult = (nextQuery: string) => {
    setQuery(nextQuery);
  };

  const handleModeChange = (next: UiMode) => {
    if (next === '0243' || next === '02493') {
      setLast0243Mode(next);
    }
    setMode(next);
  };

  const synLayout = mode === 'synonym';

  const resultsLabel = useMemo(() => {
    if (synLayout && results.length > 0) {
      return synResultsStats(results);
    }
    if (total != null && total > results.length) {
      return `已載入 ${results.length} / ${total} 個結果`;
    }
    if (results.length > 0) {
      return `${results.length} 個結果`;
    }
    return '';
  }, [synLayout, results, total]);

  const emptyMessage = useMemo(() => {
    if (!trimmedQuery || searchLoading || results.length > 0 || offlineStatus !== 'ready') {
      return null;
    }
    return formatEmptySearchMessage(trimmedQuery, displayHint, mode);
  }, [trimmedQuery, searchLoading, results.length, offlineStatus, displayHint, mode]);

  const toggleStats = () => {
    setShowStats(!showStats);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Canto-0243 PWA</h1>
        <p className="subtitle">粵語填詞查詢工具</p>

        <div className="db-status">
          {offlineStatus === 'preparing' && (
            <div className="status-loading">
              <span>載入資料庫: {progress}%</span>
              <progress value={progress} max="100" />
            </div>
          )}
          {offlineStatus === 'ready' && (
            <span className="status-ready">
              ✓ 資料庫就緒（詞庫版本：{lexiconVersion}
              {(import.meta as ImportMeta).env?.VITE_DB_BACKEND === 'opfs' ? ' · OPFS' : ''}）
            </span>
          )}
          {offlineStatus === 'not_ready' && (
            <div className="status-loading">
              <span>
                {isOnline
                  ? '尚未離線就緒（首次使用需下載一次資料）'
                  : isDbCached
                    ? '偵測到離線緩存，但尚未初始化（可嘗試重試）'
                    : '離線未就緒（需要一次上線完成離線就緒）'}
              </span>
              {isOnline && !isDbCached && (
                <span style={{ display: 'block', opacity: 0.85, marginTop: 6 }}>
                  提示：首次離線就緒需下載較大資料包，建議用 Wi‑Fi。
                  {isLikelyMetered ? '（偵測到可能為省流量/慢速網路）' : ''}
                </span>
              )}
              <button type="button" className="stats-toggle" onClick={retryOfflineReady}>
                重新嘗試離線就緒
              </button>
            </div>
          )}
          {offlineStatus === 'failed' && (
            <div className="status-error">
              <span>✗ 離線就緒失敗: {dbError?.message}</span>
              <button type="button" className="stats-toggle" onClick={retryOfflineReady}>
                重試
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="app-main">
        <form onSubmit={(e) => e.preventDefault()} className="search-form">
          <div className="search-controls">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="輸入 0243 碼、粵拼 或 漢字..."
              className="search-input"
              disabled={offlineStatus === 'preparing'}
              autoFocus
            />
            <div className="mode-selector">
              <label>
                <input
                  type="radio"
                  checked={mode === '0243'}
                  onChange={() => handleModeChange('0243')}
                  disabled={!isReady}
                />
                0243模式
              </label>
              <label>
                <input
                  type="radio"
                  checked={mode === '02493'}
                  onChange={() => handleModeChange('02493')}
                  disabled={!isReady}
                />
                02493模式
              </label>
              <label>
                <input
                  type="radio"
                  checked={mode === 'synonym'}
                  onChange={() => handleModeChange('synonym')}
                  disabled={!isReady}
                />
                近反義
              </label>
            </div>
          </div>
          <button type="submit" className="search-button" disabled={!isReady || !trimmedQuery}>
            搜尋
          </button>
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

        <button onClick={toggleStats} className="stats-toggle">
          {showStats ? '隱藏統計' : '顯示資料庫統計'}
        </button>

        {showStats && stats && (
          <div className="db-stats">
            <p>詞條數量: {stats.wordCount.toLocaleString()}</p>
            <p>資料表數量: {stats.tableCount}</p>
          </div>
        )}

        <div className="search-results">
          {displayHint && results.length > 0 && <p className="search-hint">{displayHint}</p>}
          {searchLoading && <p className="loading">搜尋中...</p>}
          {searchError && <p className="error">錯誤: {searchError.message}</p>}

          {results.length > 0 && (
            <div className="results-list">
              {resultsLabel && <p className="results-count">{resultsLabel}</p>}
              {synLayout ? (
                <SynResultList results={results} onPick={handlePickResult} />
              ) : (
                <ResultList results={results} onPick={handlePickResult} />
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
            <div className="no-results">
              <p>
                <strong>{emptyMessage.primary}</strong>
              </p>
              {emptyMessage.secondary ? <p>{emptyMessage.secondary}</p> : null}
            </div>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>Canto-0243 PWA v0.1.0</p>
        <p>離線粵語填詞查詢工具 · 詞庫版本：{lexiconVersion}</p>
      </footer>
    </div>
  );
}

export default App;
