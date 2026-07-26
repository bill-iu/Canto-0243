import type { QueryOptions, QueryResult, SearchPageResult } from '../db/query.ts';
import { last0243UiToUrlMode, uiModeToUrlMode, type Last0243SearchMode } from '../mode-meta.ts';

const HINT_UTF8_PREFIX = "UTF-8''";

export interface QueryWorkspaceQueryRequest {
  query: string;
  mode: QueryOptions['mode'];
  limit: number;
  offset: number;
  fallback_0243_mode?: Last0243SearchMode;
  pzmode?: 'm1' | 'm2' | 'm3';
  ui_lang?: 'zh' | 'zh-Hans' | 'en';
  signal?: AbortSignal;
}

export interface QueryWorkspaceQueryPage {
  items: QueryResult[];
  total: number | null;
  hint: string | null;
}

export interface QueryWorkspaceQueryAdapter {
  searchPage(request: QueryWorkspaceQueryRequest): Promise<QueryWorkspaceQueryPage>;
}

export type SearchPageLoader = (request: QueryOptions) => Promise<SearchPageResult>;

export function createDatabaseQueryWorkspaceAdapter(
  loadPage: SearchPageLoader,
): QueryWorkspaceQueryAdapter {
  return {
    async searchPage(request) {
      if (request.signal?.aborted) {
        throw new DOMException('Search aborted', 'AbortError');
      }
      const page = await loadPage({
        query: request.query,
        mode: request.mode,
        limit: request.limit,
        offset: request.offset,
        fallback_0243_mode: request.fallback_0243_mode,
        pzmode: request.pzmode,
        ui_lang: request.ui_lang,
        shouldCancel: () => request.signal?.aborted === true,
      });
      if (request.signal?.aborted) {
        throw new DOMException('Search aborted', 'AbortError');
      }
      return {
        items: page.items,
        total: page.total ?? null,
        hint: page.hint ?? null,
      };
    },
  };
}

export interface PortableWordRead {
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

export type QueryWorkspaceFetch = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export function decodeQueryWorkspaceHint(raw: string | null): string | null {
  if (!raw) return raw;
  if (!raw.startsWith(HINT_UTF8_PREFIX)) return raw;
  try {
    return decodeURIComponent(raw.slice(HINT_UTF8_PREFIX.length));
  } catch {
    return raw;
  }
}

export function mapPortableWordRead(item: PortableWordRead): QueryResult {
  return {
    word: item.char,
    jyutping: item.jyutping,
    code: item.code,
    score: item.score ?? 0,
    resultType: (item.result_type as QueryResult['resultType']) ?? undefined,
    anchor_dimension: (item.anchor_dimension as QueryResult['anchor_dimension']) ?? undefined,
    relation: (item.relation as QueryResult['relation']) ?? undefined,
    in_db: item.in_db ?? undefined,
    source: item.source ?? undefined,
  };
}

function portableMode(mode: QueryOptions['mode']): string {
  return uiModeToUrlMode((mode ?? '0243') as Parameters<typeof uiModeToUrlMode>[0]);
}

export function buildQueryWorkspacePortableUrl(request: QueryWorkspaceQueryRequest): string {
  const urlMode = portableMode(request.mode);
  let url =
    `/words/search/?q=${encodeURIComponent(request.query)}` +
    `&mode=${encodeURIComponent(urlMode)}` +
    `&limit=${request.limit}` +
    `&offset=${request.offset}`;
  if (urlMode === 'pz' && request.pzmode) {
    url += `&pzmode=${encodeURIComponent(request.pzmode)}`;
  }
  if (urlMode === 'syn' && request.fallback_0243_mode) {
    url += `&fallback_0243_mode=${encodeURIComponent(
      last0243UiToUrlMode(request.fallback_0243_mode),
    )}`;
  }
  return url;
}

export function createPortableQueryWorkspaceAdapter(
  fetchImpl: QueryWorkspaceFetch = (input, init) => fetch(input, init),
): QueryWorkspaceQueryAdapter {
  return {
    async searchPage(request) {
      const response = await fetchImpl(buildQueryWorkspacePortableUrl(request), {
        signal: request.signal,
      });
      if (!response.ok) throw new Error(`後端回應失敗 (${response.status})`);
      const data = (await response.json()) as PortableWordRead[];
      const totalHeader = response.headers.get('X-Search-Total');
      const parsedTotal = totalHeader ? Number.parseInt(totalHeader, 10) : NaN;
      return {
        items: Array.isArray(data) ? data.map(mapPortableWordRead) : [],
        total: Number.isFinite(parsedTotal) ? parsedTotal : null,
        hint: decodeQueryWorkspaceHint(response.headers.get('X-Search-Hint')),
      };
    },
  };
}
