import { uiModeToUrlMode, urlModeToUiMode, type UiMode } from './mode-meta';

export type AppView = 'search' | 'guide' | 'about';

export interface ParsedSearchUrl {
  q: string;
  mode: UiMode;
  view: AppView;
}

function parseAppView(raw: string | null): AppView {
  if (raw === 'guide') return 'guide';
  if (raw === 'about') return 'about';
  return 'search';
}

export function parseSearchUrl(search: string): ParsedSearchUrl {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
  const view = parseAppView(params.get('view'));
  return {
    q: view === 'search' ? params.get('q') || '' : '',
    mode: urlModeToUiMode(params.get('mode')),
    view,
  };
}

export function buildAppQueryString(options: {
  q?: string;
  mode?: UiMode;
  view?: AppView;
}): string {
  const view = options.view ?? 'search';
  const params = new URLSearchParams();
  if (view === 'guide') {
    params.set('view', 'guide');
    return params.toString();
  }
  if (view === 'about') {
    params.set('view', 'about');
    return params.toString();
  }
  const mode = options.mode ?? '0243';
  const trimmed = (options.q ?? '').trim();
  const urlMode = uiModeToUrlMode(mode);
  if (urlMode !== 'm1') {
    params.set('mode', urlMode);
  }
  if (trimmed) {
    params.set('q', trimmed);
  }
  return params.toString();
}

export function buildSearchQueryString(q: string, mode: UiMode): string {
  return buildAppQueryString({ q, mode, view: 'search' });
}

export function replaceAppUrl(options: { q: string; mode: UiMode; view: AppView }): void {
  if (typeof window === 'undefined') return;
  const qs = buildAppQueryString(options);
  const suffix = qs ? `?${qs}` : '';
  const next = `${window.location.pathname}${suffix}${window.location.hash}`;
  window.history.replaceState(window.history.state, '', next);
}

export function replaceSearchUrl(q: string, mode: UiMode): void {
  replaceAppUrl({ q, mode, view: 'search' });
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
  if (parsed.q !== '開心' || parsed.mode !== 'synonym' || parsed.view !== 'search') {
    throw new Error(`searchUrlSelfCheck: parse ${parsed.q} ${parsed.mode} ${parsed.view}`);
  }
  const m2 = parseSearchUrl('?mode=m2&q=23');
  if (m2.mode !== '02493' || m2.q !== '23' || m2.view !== 'search') {
    throw new Error('searchUrlSelfCheck: m2 parse');
  }
  const guideQs = buildAppQueryString({ view: 'guide' });
  if (guideQs !== 'view=guide') {
    throw new Error(`searchUrlSelfCheck: guide qs ${guideQs}`);
  }
  const aboutParsed = parseSearchUrl('?view=about');
  if (aboutParsed.view !== 'about' || aboutParsed.q !== '') {
    throw new Error('searchUrlSelfCheck: about parse');
  }
  const guideParsed = parseSearchUrl('?view=guide&q=ignored');
  if (guideParsed.view !== 'guide' || guideParsed.q !== '') {
    throw new Error('searchUrlSelfCheck: guide ignores q');
  }
}
