import {
  VIEW,
  buildUrlSearchParams,
  parseUrlSearchParams,
  searchParamsWithoutBoot,
  type QueryTab,
} from '../../shared/query-tabs-state.mjs';
import { uiModeToUrlMode, urlModeToUiMode, type PingzeSubMode, type UiMode } from './mode-meta';

export type AppView = 'search' | 'guide' | 'about';

export interface ParsedSearchUrl {
  q: string;
  mode: UiMode;
  pzmode: PingzeSubMode;
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
    pzmode: parsed.pzmode as PingzeSubMode,
    view: appViewFromShared(parsed.view),
  };
}

export function tabForAppUrl(options: {
  q?: string;
  mode?: UiMode;
  pzmode?: PingzeSubMode;
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
  pzmode?: PingzeSubMode;
  view?: AppView;
}): string {
  const tab = tabForAppUrl(options);
  const params = buildUrlSearchParams(tab, uiModeToUrlMode(options.mode ?? '0243'), options.pzmode);
  return params.toString();
}

export function buildSearchQueryString(q: string, mode: UiMode, pzmode?: PingzeSubMode): string {
  return buildAppQueryString({ q, mode, pzmode, view: 'search' });
}

export function replaceAppUrl(options: { q: string; mode: UiMode; pzmode?: PingzeSubMode; view: AppView }): void {
  if (typeof window === 'undefined') return;
  const qs = buildAppQueryString(options);
  const suffix = qs ? `?${qs}` : '';
  const next = `${window.location.pathname}${suffix}${window.location.hash}`;
  window.history.replaceState(window.history.state, '', next);
}

export function replaceSearchUrl(q: string, mode: UiMode, pzmode?: PingzeSubMode): void {
  replaceAppUrl({ q, mode, pzmode, view: 'search' });
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
  const m3 = parseSearchUrl('?mode=m3&q=45');
  if (m3.mode !== '394052' || m3.q !== '45') {
    throw new Error('searchUrlSelfCheck: m3 parse');
  }
  const m3qs = buildSearchQueryString('45', '394052');
  if (!m3qs.includes('mode=m3')) {
    throw new Error(`searchUrlSelfCheck: m3 qs ${m3qs}`);
  }
  const pz = parseSearchUrl('?mode=pz&q=PZ%3F');
  if (pz.mode !== 'pingze' || pz.pzmode !== 'm1' || pz.q !== 'PZ?') {
    throw new Error('searchUrlSelfCheck: pz default parse');
  }
  const pzqs = buildSearchQueryString('PZ3', 'pingze', 'm2');
  if (!pzqs.includes('mode=pz') || !pzqs.includes('pzmode=m2')) {
    throw new Error(`searchUrlSelfCheck: pz qs ${pzqs}`);
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
