/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect } from 'react';
import { useDB, useSearch } from './hooks/useDB.tsx';
import type { QueryOptions } from './hooks/useDB.tsx';
import './App.css';

function App() {
  const lexiconVersion = (import.meta as any).env?.VITE_LEXICON_VERSION || 'dev';
  const conn = (navigator as any).connection;
  const isLikelyMetered =
    Boolean(conn?.saveData) ||
    (typeof conn?.effectiveType === 'string' && /(^|-)2g$/.test(conn.effectiveType));

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'0243' | '02493' | 'synonym'>('0243');
  const [showStats, setShowStats] = useState(false);
  
  const { 
    isReady, 
    status, 
    offlineStatus,
    isOnline,
    isDbCached,
    progress, 
    error: dbError,
    initialize,
    retryOfflineReady,
    getStats 
  } = useDB();
  
  const { 
    results, 
    loading: searchLoading, 
    error: searchError
  } = useSearch(query ? { query, mode, limit: 50 } : null);

  // Auto-initialize database on mount
  useEffect(() => {
    // Auto mode: only attempt when we are online, or when a cached DB likely exists.
    // Otherwise, stay "not ready" with a clear message until user reconnects.
    if (isOnline || isDbCached) {
      initialize();
    }
  }, [initialize, isOnline, isDbCached]);

  // Load database stats
  const [stats, setStats] = useState<{ wordCount: number; tableCount: number } | null>(null);
  useEffect(() => {
    if (isReady && showStats && !stats) {
      getStats().then(setStats).catch(console.error);
    }
  }, [isReady, showStats, stats, getStats]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Search is triggered automatically by useSearch hook
  };

  const toggleStats = () => {
    setShowStats(!showStats);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Canto-0243 PWA</h1>
        <p className="subtitle">粵語填詞查詢工具</p>
        
        {/* Database Status */}
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
        <form onSubmit={handleSearch} className="search-form">
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
                  onChange={() => setMode('0243')}
                  disabled={!isReady}
                />
                0243模式
              </label>
              <label>
                <input
                  type="radio"
                  checked={mode === '02493'}
                  onChange={() => setMode('02493')}
                  disabled={!isReady}
                />
                02493模式
              </label>
              <label>
                <input
                  type="radio"
                  checked={mode === 'synonym'}
                  onChange={() => setMode('synonym')}
                  disabled={!isReady}
                />
                近反義
              </label>
            </div>
          </div>
          <button 
            type="submit" 
            className="search-button"
            disabled={!isReady || !query.trim()}
          >
            搜尋
          </button>
        </form>

        {/* Stats Toggle */}
        <button onClick={toggleStats} className="stats-toggle">
          {showStats ? '隱藏統計' : '顯示資料庫統計'}
        </button>
        
        {showStats && stats && (
          <div className="db-stats">
            <p>詞條數量: {stats.wordCount.toLocaleString()}</p>
            <p>資料表數量: {stats.tableCount}</p>
          </div>
        )}

        {/* Search Results */}
        <div className="search-results">
          {searchLoading && <p className="loading">搜尋中...</p>}
          {searchError && <p className="error">錯誤: {searchError.message}</p>}
          
          {results.length > 0 && (
            <div className="results-list">
              <p className="results-count">找到 {results.length} 個結果</p>
              <ul>
                {results.map((result, index) => (
                  <li key={index} className="result-item">
                    <span className="word">{result.word}</span>
                    <span className="jyutping">{result.jyutping}</span>
                    <span className="code">{result.code}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {results.length === 0 && query && !searchLoading && offlineStatus === 'ready' && (
            <p className="no-results">未找到結果</p>
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
