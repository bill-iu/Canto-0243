/** Ambient types for Portable .mjs modules (contract: tests/query_tabs_state_test.mjs). */
declare module '@shared/query-tabs' {
  export const SESSION_KEY: string;
  export const TAB_LABEL_MAX: number;
  export const VIEW: Readonly<{
    SEARCH: string;
    GUIDE: string;
    RELATION: string;
    CORRECTIONS: string;
    ABOUT: string;
  }>;
  export const LAUNCHER_BOOT_PARAM: string;

  export interface QueryTab {
    id: number;
    view: string;
    q: string;
    results: unknown[];
    offset: number;
    total: number | null;
    historyStack?: { q: string; mode: string }[];
    historyIndex?: number;
    relation?: Record<string, string>;
    prefetchChar?: string;
  }

  export interface TabState {
    activeId: number;
    nextTabId: number;
    tabs: QueryTab[];
  }

  export function tabLabel(tab: QueryTab, lang?: 'zh' | 'en'): string;
  export function findTabByView(tabs: QueryTab[], view: string): QueryTab | null;
  export function createSearchTab(opts?: Partial<QueryTab>): QueryTab;
  export function createGuideTab(opts?: { id?: number }): QueryTab;
  export function createAboutTab(opts?: { id?: number }): QueryTab;
  export function openSingletonView(
    state: TabState,
    view: string,
    createTab: (opts: { id: number }) => QueryTab,
  ): TabState;
  export function buildUrlSearchParams(tab: QueryTab, mode?: string): URLSearchParams;
  export function parseUrlSearchParams(params: URLSearchParams): {
    q: string;
    mode: string;
    view: string;
  };
  export function searchParamsWithoutBoot(params: URLSearchParams): URLSearchParams | null;
  export function serializeSession(state: TabState): string;
  export function deserializeSession(raw: string): TabState;
  export function closeTab(state: TabState, tabId: number): TabState;
  export function reorderTab(state: TabState, fromIndex: number, toIndex: number): TabState;
  export function reorderTabsByIds(state: TabState, orderedIds: number[]): TabState;
  export function applyUrlToTabs(
    existingState: TabState | null,
    parsed: ReturnType<typeof parseUrlSearchParams>,
  ): TabState;
}

declare module '../../frontend/guide-i18n.mjs' {
  export function getGuideHero(lang: 'zh' | 'en'): { eyebrow: string; title: string; lede: string };
  export function getGuideIntro(lang: 'zh' | 'en'): { title: string; paragraphs: string[] };
  export function getGuideSections(lang: 'zh' | 'en'): Array<{
    id: string;
    title: string;
    intro: string;
    examples: Array<{ query: string; mode: string; label: string; title?: string }>;
  }>;
  export function renderGuideGridHtml(lang: 'zh' | 'en'): string;
  export function applyGuideLang(lang: 'zh' | 'en'): void;
}

declare module '../../frontend/about-i18n.mjs' {
  export const ABOUT_COPY: Record<'zh' | 'en', Record<string, string>>;
  export function getAboutCopy(lang: 'zh' | 'en'): Record<string, string>;
  export function applyAboutLang(lang: 'zh' | 'en'): void;
}

declare module '../../frontend/mode-i18n.mjs' {
  export type UrlMode = 'm1' | 'm2' | 'm3' | 'syn';
  export interface ModeMeta {
    title: string;
    note: string;
    readout: string;
    statsLabel: string;
    placeholder: string;
  }
  export const MODE_META: Record<UrlMode, ModeMeta>;
  export function getModeMeta(mode: string, lang?: 'zh' | 'en'): ModeMeta;
  export function modeHelp(mode: UrlMode, lang?: 'zh' | 'en'): string;
  export function modeRedirectHint(mode: 'm1' | 'm2' | 'm3', lang?: 'zh' | 'en'): string;
  export function syncPortableModeMenu(lang?: 'zh' | 'en'): void;
}

declare module '@shared/search-navigation' {
  import type { QueryTab } from '@shared/query-tabs';

  export function ensureSearchTabHistory(tab: QueryTab, defaultMode?: string): QueryTab;
  export function currentSearchHistoryFrame(tab: QueryTab): { q: string; mode: string };
  export function commitSearchHistoryFrame(
    tab: QueryTab,
    frame: { q: string; mode: string },
  ): { pushed: boolean; frame: { q: string; mode: string } };
  export function stepSearchTabBack(tab: QueryTab): { q: string; mode: string } | null;
  export function isHistoryForward(lastSeq: number | undefined, state: unknown): boolean;
  export function shouldApplySearchPopstate(activeTab: QueryTab | null, state: unknown): boolean;
  export function resetSearchTabHistory(tab: QueryTab, mode?: string): QueryTab;
  export function buildHistoryStateForTab(
    tab: QueryTab,
    mode?: string,
  ): { tabId: number; view: string; query: string; mode: string };
  export function shouldPushSearchHistory(next: unknown, prev: unknown): boolean;
}
