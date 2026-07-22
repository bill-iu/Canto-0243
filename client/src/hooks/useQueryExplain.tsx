import { useEffect, useState } from 'react';

import { explainQuery, type QueryExplainResult } from '../db/query-explain';

const DEBOUNCE_MS = 250;
const EMPTY: QueryExplainResult = { summary: null, warning: null, kind: null };

/** Map UI mode → explain/parse mode (對齊 Portable `/words/query/explain?mode=`). */
export function uiModeToExplainMode(mode: string): string {
  if (mode === 'pingze' || mode === 'pz') return 'pz';
  if (mode === 'synonym' || mode === 'syn') return 'syn';
  if (mode === '02493' || mode === 'm2') return 'm2';
  if (mode === '394052' || mode === 'm3') return 'm3';
  return 'm1';
}

/** 查詢語意解釋 — 唔等 DB；250ms debounce（對齊桌面 query-explain.mjs） */
export function useQueryExplain(query: string, mode: string = 'm1'): QueryExplainResult {
  const trimmed = query.trim();
  const explainMode = uiModeToExplainMode(mode);
  const [result, setResult] = useState<QueryExplainResult>(EMPTY);

  useEffect(() => {
    if (!trimmed) {
      setResult(EMPTY);
      return;
    }
    const timer = setTimeout(() => {
      setResult(explainQuery(trimmed, explainMode));
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [trimmed, explainMode]);

  return result;
}
