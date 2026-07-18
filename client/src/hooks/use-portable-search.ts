/**
 * Portable host: GET /words/search/ → same outward shape as useSearch.
 */
import {
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import type { QueryOptions, QueryResult } from '../db/query';
import {
  SEARCH_FIRST_PAGE_SIZE,
  searchLimitForOffset,
} from '../db/query';
import {
  last0243UiToUrlMode,
  uiModeToUrlMode,
  type Last0243SearchMode,
  type UiMode,
  type UrlMode,
} from '../mode-meta';
import { DBContext } from './db-context.ts';
import { markSearchDispatch, markSearchResolve } from '../search-perf.ts';

const SEARCH_LOADING_LABEL_DELAY_MS = 150;
const HINT_UTF8_PREFIX = "UTF-8''";

export interface WordReadLike {
  char: string;
  code: string;
  jyutping: string;
  score?: number | null;
  result_type?: string | null;
  relation?: string | null;
  in_db?: boolean | null;
  source?: string | null;
  anchor_dimension?: string | null;
}

export function queryModeToUrlMode(mode: QueryOptions['mode'] | undefined): UrlMode {
  return uiModeToUrlMode((mode ?? '0243') as UiMode);
}

export function decodeSearchHintHeader(raw: string | null): string | null {
  if (!raw) return raw;
  if (raw.startsWith(HINT_UTF8_PREFIX)) {
    try {
      return decodeURIComponent(raw.slice(HINT_UTF8_PREFIX.length));
    } catch {
      return raw;
    }
  }
  return raw;
}

export function mapWordReadToQueryResult(item: WordReadLike): QueryResult {
  return {
    word: item.char,
    jyutping: item.jyutping,
    code: item.code,
    score: item.score ?? undefined,
    resultType: (item.result_type as QueryResult['resultType']) ?? undefined,
    anchor_dimension: (item.anchor_dimension as QueryResult['anchor_dimension']) ?? undefined,
    relation: (item.relation as QueryResult['relation']) ?? undefined,
    in_db: item.in_db ?? undefined,
    source: item.source ?? undefined,
  };
}

export function buildPortableSearchUrl(opts: {
  query: string;
  mode: QueryOptions['mode'];
  limit: number;
  offset: number;
  fallback_0243_mode?: Last0243SearchMode;
  pzmode?: 'm1' | 'm2' | 'm3';
}): string {
  const urlMode = queryModeToUrlMode(opts.mode);
  let url =
    `/words/search/?q=${encodeURIComponent(opts.query)}` +
    `&mode=${encodeURIComponent(urlMode)}` +
    `&limit=${opts.limit}` +
    `&offset=${opts.offset}`;
  if (urlMode === 'pz' && opts.pzmode) {
    url += `&pzmode=${encodeURIComponent(opts.pzmode)}`;
  }
  if (urlMode === 'syn' && opts.fallback_0243_mode) {
    url += `&fallback_0243_mode=${encodeURIComponent(last0243UiToUrlMode(opts.fallback_0243_mode))}`;
  }
  return url;
}

async function fetchSearchPage(opts: {
  query: string;
  mode: QueryOptions['mode'];
  limit: number;
  offset: number;
  fallback_0243_mode?: Last0243SearchMode;
  pzmode?: 'm1' | 'm2' | 'm3';
  signal?: AbortSignal;
}): Promise<{ items: QueryResult[]; total: number | null; hint: string | null }> {
  const url = buildPortableSearchUrl(opts);
  const res = await fetch(url, { signal: opts.signal });
  if (!res.ok) throw new Error(`後端回應失敗 (${res.status})`);
  const data = (await res.json()) as WordReadLike[];
  const totalHeader = res.headers.get('X-Search-Total');
  const total = totalHeader ? Number.parseInt(totalHeader, 10) : null;
  const hint = decodeSearchHintHeader(res.headers.get('X-Search-Hint'));
  return {
    items: Array.isArray(data) ? data.map(mapWordReadToQueryResult) : [],
    total: Number.isFinite(total as number) ? total : null,
    hint,
  };
}

/** ponytail: runnable check — import { portableSearchSelfCheck } from '…' */
export function portableSearchSelfCheck(): void {
  const url = buildPortableSearchUrl({
    query: '事業',
    mode: '02493',
    limit: 10,
    offset: 0,
  });
  if (!url.includes('mode=m2') || !url.includes('q=%E4%BA%8B%E6%A5%AD')) {
    throw new Error('portableSearchSelfCheck: url mode/q');
  }
  const syn = buildPortableSearchUrl({
    query: '愛',
    mode: 'synonym',
    limit: 20,
    offset: 0,
    fallback_0243_mode: '394052',
  });
  if (!syn.includes('mode=syn') || !syn.includes('fallback_0243_mode=m3')) {
    throw new Error('portableSearchSelfCheck: syn fallback');
  }
  const mapped = mapWordReadToQueryResult({
    char: '甲',
    code: '1',
    jyutping: 'gaap3',
    result_type: 'word',
  });
  if (mapped.word !== '甲' || mapped.resultType !== 'word') {
    throw new Error('portableSearchSelfCheck: WordRead→QueryResult');
  }
  if (decodeSearchHintHeader("UTF-8''%E6%B8%AC") !== '測') {
    throw new Error('portableSearchSelfCheck: hint decode');
  }
}

export function usePortableSearch(
  query: string,
  mode: QueryOptions['mode'] = '0243',
  options?: {
    pageSize?: number;
    fallback_0243_mode?: '0243' | '02493' | '394052';
    pzmode?: 'm1' | 'm2' | 'm3';
    ui_lang?: 'zh' | 'en';
  },
) {
  const fallback0243Mode = options?.fallback_0243_mode;
  const pzmode = options?.pzmode;
  const db = useContext(DBContext);
  const isReady = db?.isReady ?? false;
  const status = db?.status ?? 'idle';
  const [results, setResults] = useState<QueryResult[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingVisible, setLoadingVisible] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchError, setSearchError] = useState<Error | null>(null);
  const [lastPageSize, setLastPageSize] = useState(0);
  const genRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const trimmed = query.trim();
  const canSearch = Boolean(trimmed) && isReady;
  const firstPageLimit = options?.pageSize ?? searchLimitForOffset(mode, 0);
  const morePageLimit = options?.pageSize ?? searchLimitForOffset(mode, 1);
  const hasMoreThreshold = mode === 'synonym' ? morePageLimit : SEARCH_FIRST_PAGE_SIZE;

  const hasMore =
    canSearch &&
    ((total != null && results.length < total) ||
      (total == null && lastPageSize >= hasMoreThreshold));

  useLayoutEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;

    if (!canSearch) {
      genRef.current += 1;
      setResults([]);
      setTotal(null);
      setHint(null);
      setLoading(false);
      setLastPageSize(0);
      return;
    }

    const gen = ++genRef.current;
    const shouldCancel = () => gen !== genRef.current;
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setSearchError(null);

    void (async () => {
      markSearchDispatch();
      try {
        const page = await fetchSearchPage({
          query: trimmed,
          mode,
          limit: firstPageLimit,
          offset: 0,
          fallback_0243_mode: fallback0243Mode,
          pzmode,
          signal: ac.signal,
        });
        if (shouldCancel()) return;
        markSearchResolve();
        setResults(page.items);
        setTotal(page.total);
        setHint(page.hint);
        setLastPageSize(page.items.length);
      } catch (err) {
        if (shouldCancel() || (err instanceof DOMException && err.name === 'AbortError')) return;
        markSearchResolve();
        setSearchError(err instanceof Error ? err : new Error(String(err)));
        setResults([]);
        setTotal(null);
        setHint(null);
        setLastPageSize(0);
      } finally {
        if (!shouldCancel()) setLoading(false);
      }
    })();

    return () => {
      genRef.current += 1;
      ac.abort();
    };
  }, [trimmed, mode, firstPageLimit, canSearch, fallback0243Mode, pzmode]);

  const isLoading = loading || status === 'loading';

  useEffect(() => {
    if (!isLoading) {
      setLoadingVisible(false);
      return;
    }
    const timer = window.setTimeout(() => setLoadingVisible(true), SEARCH_LOADING_LABEL_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [isLoading]);

  const loadMore = useCallback(async () => {
    if (!canSearch || loading || loadingMore || !hasMore) return;
    const gen = genRef.current;
    const shouldCancel = () => gen !== genRef.current;
    setLoadingMore(true);
    setSearchError(null);
    try {
      const page = await fetchSearchPage({
        query: trimmed,
        mode,
        limit: morePageLimit,
        offset: results.length,
        fallback_0243_mode: fallback0243Mode,
        pzmode,
      });
      if (shouldCancel()) return;
      setResults((prev) => [...prev, ...page.items]);
      if (page.total != null) setTotal(page.total);
      setLastPageSize(page.items.length);
    } catch (err) {
      if (shouldCancel()) return;
      setSearchError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      if (!shouldCancel()) setLoadingMore(false);
    }
  }, [
    canSearch,
    loading,
    loadingMore,
    hasMore,
    trimmed,
    mode,
    morePageLimit,
    results.length,
    fallback0243Mode,
    pzmode,
  ]);

  return {
    results,
    total,
    hint,
    loading: isLoading,
    loadingVisible,
    loadingMore,
    error: searchError,
    isReady,
    hasMore,
    loadMore,
  };
}
