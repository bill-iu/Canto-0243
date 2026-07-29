import { useEffect, useState } from 'react';

import { explainQuery, type QueryExplainResult } from '../db/query-explain';
import { isPortableHost } from '../host-mode.ts';
import { useUiRhymeProfile } from '../rhyme-profile-ui.ts';

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

export function buildPortableExplainUrl(
  query: string,
  mode: string,
  rhymeProfile: string = 'exact',
  pzmode?: string,
): string {
  const explainMode = uiModeToExplainMode(mode);
  let url =
    `/words/query/explain?q=${encodeURIComponent(query)}` +
    `&mode=${encodeURIComponent(explainMode)}`;
  if (explainMode === 'pz' && pzmode) {
    url += `&pzmode=${encodeURIComponent(pzmode)}`;
  }
  if (rhymeProfile && rhymeProfile !== 'exact') {
    url += `&rhyme_profile=${encodeURIComponent(rhymeProfile)}`;
  }
  return url;
}

async function fetchPortableExplain(
  query: string,
  mode: string,
  rhymeProfile: string,
  signal?: AbortSignal,
): Promise<QueryExplainResult> {
  const res = await fetch(buildPortableExplainUrl(query, mode, rhymeProfile), { signal });
  if (!res.ok) throw new Error(`解釋 API 失敗 (${res.status})`);
  const data = (await res.json()) as {
    summary?: string | null;
    warning?: string | null;
    kind?: string | null;
  };
  return {
    summary: data.summary ?? null,
    warning: data.warning ?? null,
    kind: data.kind ?? null,
  };
}

/** 查詢語意解釋 — 唔等 DB；250ms debounce。Portable 走 `/words/query/explain`（含 rhyme_profile）。 */
export function useQueryExplain(query: string, mode: string = 'm1'): QueryExplainResult {
  const trimmed = query.trim();
  const explainMode = uiModeToExplainMode(mode);
  const [rhymeProfile] = useUiRhymeProfile();
  const [result, setResult] = useState<QueryExplainResult>(EMPTY);

  useEffect(() => {
    if (!trimmed) {
      setResult(EMPTY);
      return;
    }
    const ac = new AbortController();
    const timer = setTimeout(() => {
      if (isPortableHost()) {
        void fetchPortableExplain(trimmed, mode, rhymeProfile, ac.signal)
          .then((next) => {
            if (!ac.signal.aborted) setResult(next);
          })
          .catch(() => {
            if (!ac.signal.aborted) {
              // 後端解釋失敗時回退本地（仍傳 rhyme_profile）
              setResult(explainQuery(trimmed, explainMode, rhymeProfile));
            }
          });
        return;
      }
      setResult(explainQuery(trimmed, explainMode, rhymeProfile));
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      ac.abort();
    };
  }, [trimmed, explainMode, mode, rhymeProfile]);

  return result;
}
