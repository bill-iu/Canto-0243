/**
 * Canto-0243 PWA - Main Application
 * Progressive Web App for Cantonese lyric query
 */

import { useState, useEffect } from 'react';
import { useDB, useSearch, QueryOptions } from './hooks/useDB';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'0243' | '02493' | 'synonym'>('0243');
  const [showStats, setShowStats] = useState(false);
  
  const { 
    isReady, 
    status, 
    progress, 
    error: dbError,
    initialize,
    getStats 
  } = useDB();
  
  const { 
    results, 
    loading: searchLoading, 
    error: searchError
  } = useSearch(query ? { query, mode, limit: 50 } : null);

  // Auto-initialize database on mount
  useEffect(() => {
    initialize();
  }, [initialize]);

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
          {status === 'loading' && (
            <div className="status-loading">
              <span>載入資料庫: {progress}%</span>
              <progress value={progress} max="100" />
            </div>
          )}
          {status === 'ready' && (
            <span className="status-ready">✓ 資料庫就緒</span>
          )}
          {status === 'error' && (
            <span className="status-error">✗ 錯誤: {dbError?.message}</span>
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
              disabled={status === 'loading'}
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
          
          {results.length === 0 && query && !searchLoading && (
            <p className="no-results">未找到結果</p>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>Canto-0243 PWA v0.1.0</p>
        <p>離線粵語填詞查詢工具</p>
      </footer>
    </div>
  );
}

export default App;
