/**
 * React Hook for Database Management
 * Provides easy access to the SQL.js database in React components
 */

import { useState, useEffect, useCallback } from 'react';
import {
  initializeDatabase,
  getDatabase,
  isDatabaseInitialized,
  resetDatabase
} from '../db/init';
import {
  search,
  getDatabaseStats,
  QueryOptions,
  QueryResult,
  QueryMode,
  QueryKind,
  normalizeQuery,
  parseQuery,
  normalizeAndParse
} from '../db/query';

// Re-export query engine types and functions for convenience
export type { QueryMode, QueryKind };
export { normalizeQuery, parseQuery, normalizeAndParse };;

/**
 * Database status type
 */
export type DatabaseStatus = 'idle' | 'loading' | 'ready' | 'error';

/**
 * Database hook return type
 */
export interface UseDBReturn {
  status: DatabaseStatus;
  progress: number;
  error: Error | null;
  isReady: boolean;
  initialize: () => Promise<void>;
  search: (options: QueryOptions) => Promise<QueryResult[]>;
  getStats: () => Promise<{ wordCount: number; tableCount: number }>;
  reset: () => void;
}

/**
 * Custom hook for managing the SQL.js database
 */
export function useDB(): UseDBReturn {
  const [status, setStatus] = useState<DatabaseStatus>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Initialize the database
   */
  const initialize = useCallback(async () => {
    if (status === 'ready' || status === 'loading') {
      return;
    }

    try {
      setStatus('loading');
      setError(null);
      setProgress(0);

      // Initialize database - progress will be updated via httpvfs
      await initializeDatabase();
      
      setStatus('ready');
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      setStatus('error');
      setProgress(0);
    }
  }, [status]);

  /**
   * Execute a search query
   */
  const searchQuery = useCallback(async (options: QueryOptions) => {
    // Auto-initialize if not ready
    if (status === 'idle') {
      await initialize();
    }
    
    if (status !== 'ready') {
      throw new Error('Database not ready');
    }
    
    return search(options);
  }, [status, initialize]);

  /**
   * Get database statistics
   */
  const getStats = useCallback(async () => {
    if (status === 'idle') {
      await initialize();
    }
    
    if (status !== 'ready') {
      throw new Error('Database not ready');
    }
    
    return getDatabaseStats();
  }, [status, initialize]);

  /**
   * Reset the database connection
   */
  const reset = useCallback(() => {
    resetDatabase();
    setStatus('idle');
    setProgress(0);
    setError(null);
  }, []);

  // Auto-initialize on mount if not already initialized globally
  useEffect(() => {
    if (isDatabaseInitialized()) {
      setStatus('ready');
      setProgress(100);
    }
  }, []);

  return {
    status,
    progress,
    error,
    isReady: status === 'ready',
    initialize,
    search: searchQuery,
    getStats,
    reset
  };
}

/**
 * Hook for a specific query with loading state
 */
export function useSearch(queryOptions: QueryOptions | null) {
  const { search, isReady, status } = useDB();
  const [results, setResults] = useState<QueryResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<Error | null>(null);

  useEffect(() => {
    if (!queryOptions || !isReady) {
      setResults([]);
      return;
    }

    const executeSearch = async () => {
      try {
        setLoading(true);
        setSearchError(null);
        const results = await search(queryOptions);
        setResults(results);
      } catch (err) {
        setSearchError(err instanceof Error ? err : new Error(String(err)));
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    executeSearch();
  }, [queryOptions, isReady, search]);

  return {
    results,
    loading: loading || status === 'loading',
    error: searchError,
    isReady
  };
}

export default useDB;
