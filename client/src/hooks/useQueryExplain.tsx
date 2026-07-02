import { useEffect, useState } from 'react';

import { explainQuery, type QueryExplainResult } from '../db/query-explain';

const DEBOUNCE_MS = 250;
const EMPTY: QueryExplainResult = { summary: null, warning: null, kind: null };

/** 查詢語意解釋 — 唔等 DB；250ms debounce（對齊桌面 query-explain.mjs） */
export function useQueryExplain(query: string): QueryExplainResult {
  const trimmed = query.trim();
  const [result, setResult] = useState<QueryExplainResult>(EMPTY);

  useEffect(() => {
    if (!trimmed) {
      setResult(EMPTY);
      return;
    }
    const timer = setTimeout(() => {
      setResult(explainQuery(trimmed));
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [trimmed]);

  return result;
}
