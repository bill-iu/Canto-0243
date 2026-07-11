import type { ReactNode } from 'react';
import { DBContext } from './db-context.ts';
import { useDBState } from './useDB.ts';

export function DBProvider({ children }: { children: ReactNode }) {
  const value = useDBState();
  return <DBContext.Provider value={value}>{children}</DBContext.Provider>;
}
