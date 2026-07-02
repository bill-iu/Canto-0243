import { uiModeToUrlMode, urlModeToUiMode, type UiMode } from './mode-meta';

export interface ParsedSearchUrl {
  q: string;
  mode: UiMode;
}

export function parseSearchUrl(search: string): ParsedSearchUrl {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
  return {
    q: params.get('q') || '',
    mode: urlModeToUiMode(params.get('mode')),
  };
}

export function buildSearchQueryString(q: string, mode: UiMode): string {
  const params = new URLSearchParams();
  const trimmed = (q || '').trim();
  const urlMode = uiModeToUrlMode(mode);
  if (urlMode !== 'm1') {
    params.set('mode', urlMode);
  }
  if (trimmed) {
    params.set('q', trimmed);
  }
  return params.toString();
}

export function replaceSearchUrl(q: string, mode: UiMode): void {
  if (typeof window === 'undefined') return;
  const qs = buildSearchQueryString(q, mode);
  const suffix = qs ? `?${qs}` : '';
  const next = `${window.location.pathname}${suffix}${window.location.hash}`;
  window.history.replaceState(window.history.state, '', next);
}

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p4-search-shell-self-check.ts` */
export function searchUrlSelfCheck(): void {
  const qs = buildSearchQueryString('香港', '0243');
  if (qs !== 'q=%E9%A6%99%E6%B8%AF') {
    throw new Error(`searchUrlSelfCheck: default mode qs ${qs}`);
  }
  const withMode = buildSearchQueryString('開心', 'synonym');
  if (!withMode.includes('mode=syn') || !withMode.includes('q=')) {
    throw new Error(`searchUrlSelfCheck: syn qs ${withMode}`);
  }
  const parsed = parseSearchUrl(`?${withMode}`);
  if (parsed.q !== '開心' || parsed.mode !== 'synonym') {
    throw new Error(`searchUrlSelfCheck: parse ${parsed.q} ${parsed.mode}`);
  }
  const m2 = parseSearchUrl('?mode=m2&q=23');
  if (m2.mode !== '02493' || m2.q !== '23') {
    throw new Error('searchUrlSelfCheck: m2 parse');
  }
}
