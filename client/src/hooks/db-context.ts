import { createContext } from 'react';
import type { QueryOptions, QueryResult } from '../db/query';

export type DatabaseStatus = 'idle' | 'loading' | 'ready' | 'error';
export type OfflineReadinessStatus = 'not_ready' | 'preparing' | 'ready' | 'failed';

export interface UseDBReturn {
  status: DatabaseStatus;
  offlineStatus: OfflineReadinessStatus;
  isOfflineReady: boolean;
  isOnline: boolean;
  isDbCached: boolean | null;
  dbUrl: string;
  progress: number;
  tailProgress: number;
  startupComplete: boolean;
  suppressGateOverlay: boolean;
  error: Error | null;
  isReady: boolean;
  initialize: () => Promise<void>;
  retryOfflineReady: () => Promise<void>;
  search: (options: QueryOptions) => Promise<QueryResult[]>;
  getStats: () => Promise<{ wordCount: number; tableCount: number }>;
  reset: () => void;
}

export const DBContext = createContext<UseDBReturn | null>(null);
