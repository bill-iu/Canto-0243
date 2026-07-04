import {
  VIEW,
  buildUrlSearchParams,
  parseUrlSearchParams,
  searchParamsWithoutBoot,
  type QueryTab,
} from '../../frontend/query-tabs-state.mjs';
import { uiModeToUrlMode, urlModeToUiMode, type UiMode } from './mode-meta';

export type AppView = 'search' | 'guide' | 'about';

export interface ParsedSearchUrl {
  q: string;
  mode: UiMode;
  view: AppView;
}

function appViewFromShared(view: string): AppView {
  if (view === VIEW.GUIDE) return 'guide';
  if (view === VIEW.ABOUT) return 'about';
  return 'search';
}

export function parseSearchUrl(search: string): ParsedSearchUrl {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
  const parsed = parseUrlSearchParams(params);
  return {
    q: parsed.view === VIEW.SEARCH ? parsed.q : '',
    mode: urlModeToUiMode(parsed.mode),
    view: appViewFromShared(parsed.view),
  };
}

export function tabForAppUrl(options: {
  q?: string;
  mode?: UiMode;
  view?: AppView;
}): QueryTab {
  const view = options.view ?? 'search';
  if (view === 'guide') {
    return { id: 0, view: VIEW.GUIDE, q: '', results: [], offset: 0, total: null };
  }
  if (view === 'about') {
    return { id: 0, view: VIEW.ABOUT, q: '', results: [], offset: 0, total: null };
  }
  return {
    id: 0,
    view: VIEW.SEARCH,
    q: (options.q ?? '').trim(),
    results: [],
    offset: 0,
    total: null,
  };
}

export function buildAppQueryString(options: {
  q?: string;
  mode?: UiMode;
  view?: AppView;
}): string {
  const tab = tabForAppUrl(options);
  const params = buildUrlSearchParams(tab, uiModeToUrlMode(options.mode ?? '0243'));
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

export function stripLauncherBootFromUrl(): void {
  if (typeof window === 'undefined') return;
  const next = searchParamsWithoutBoot(new URLSearchParams(window.location.search));
  if (!next) return;
  const suffix = next.toString() ? `?${next.toString()}` : '';
  window.history.replaceState(
    window.history.state,
    '',
    `${window.location.pathname}${suffix}${window.location.hash}`,
  );
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
