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
    historyStack?: { q: string; mode: string; pzmode?: string }[];
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
  export function createRelationTab(opts?: {
    id?: number;
    relation?: { seed_char?: string; opposite_char?: string; relation_type?: string };
  }): QueryTab;
  export function createCorrectionsTab(opts?: { id?: number; prefetchChar?: string }): QueryTab;
  export function isCorrectionsSearchCommand(q: string): boolean;
  export function openSingletonView(
    state: TabState,
    view: string,
    createTab: (opts: { id: number }) => QueryTab,
  ): TabState;
  export function buildUrlSearchParams(tab: QueryTab, mode?: string, pzmode?: string): URLSearchParams;
  export function parseUrlSearchParams(params: URLSearchParams): {
    q: string;
    mode: string;
    pzmode: string;
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
  export function getGuideGroupLabel(group: string, lang: 'zh' | 'en'): string;
  export function getGuideTocCopy(lang: 'zh' | 'en'): { label: string; open: string; close: string };
  export function guideSectionDomId(id: string): string;
  export function getGuideSections(lang: 'zh' | 'en'): Array<{
    id: string;
    group?: 'common' | 'advanced';
    title: string;
    intro: string;
    examples: Array<{ query: string; mode: string; label: string; title?: string }>;
  }>;
  export function renderGuideGridHtml(lang: 'zh' | 'en'): string;
  export function renderGuideLayoutHtml(lang: 'zh' | 'en'): string;
  export function bindGuideNav(root: HTMLElement | null): () => void;
  export function applyGuideLang(lang: 'zh' | 'en'): void;
}

declare module '../../frontend/about-i18n.mjs' {
  export const ABOUT_COPY: Record<'zh' | 'en', Record<string, string>>;
  export function getAboutCopy(lang: 'zh' | 'en'): Record<string, string>;
  export function applyAboutLang(lang: 'zh' | 'en'): void;
}

declare module '../../frontend/mode-i18n.mjs' {
  export type UrlMode = 'm1' | 'm2' | 'm3' | 'syn' | 'pz';
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

  export function ensureSearchTabHistory(tab: QueryTab, defaultMode?: string, defaultPzMode?: string): QueryTab;
  export function currentSearchHistoryFrame(tab: QueryTab): { q: string; mode: string; pzmode?: string };
  export function commitSearchHistoryFrame(
    tab: QueryTab,
    frame: { q: string; mode: string; pzmode?: string },
  ): { pushed: boolean; frame: { q: string; mode: string; pzmode?: string } };
  export function stepSearchTabBack(tab: QueryTab): { q: string; mode: string; pzmode?: string } | null;
  export function isHistoryForward(lastSeq: number | undefined, state: unknown): boolean;
  export function shouldApplySearchPopstate(activeTab: QueryTab | null, state: unknown): boolean;
  export function resetSearchTabHistory(tab: QueryTab, mode?: string, pzmode?: string): QueryTab;
  export function buildHistoryStateForTab(
    tab: QueryTab,
    mode?: string,
  ): { tabId: number; view: string; query: string; mode: string; pzmode?: string };
  export function shouldPushSearchHistory(next: unknown, prev: unknown): boolean;
}

declare module '../../../frontend/committed-search.mjs' {
  import type { QueryTab, TabState } from '@shared/query-tabs';

  export interface CommittedSearchFrame {
    q: string;
    mode: string;
    pzmode: string;
  }

  export interface CommittedSearchTransaction {
    state: TabState;
    pushed: boolean;
  }

  export function commitActiveSearchTransaction(
    state: TabState,
    frame: CommittedSearchFrame,
  ): CommittedSearchTransaction;
  export function openCommittedSearchTabTransaction(
    state: TabState,
    frame: CommittedSearchFrame,
    createSearchTab: (options: Partial<QueryTab>) => QueryTab,
  ): CommittedSearchTransaction;
}

declare module '../../../frontend/tab-geometry.mjs' {
  export const TAB_GEOMETRY_SVG: string;
}

declare module '../../../frontend/chrome-tabs-layout.mjs' {
  export class QueryChromeTabsLayout {
    rootEl: HTMLElement;
    contentEl: HTMLElement;
    constructor(rootEl: HTMLElement);
    layout(): void;
    setupDraggabilly(callbacks?: {
      onPointerDown?: (id: number) => void;
      onReorderEnd?: (orderedIds: number[]) => void;
    }): void;
    getTabIdsFromDom(): number[];
  }
}

declare module '*.js?url' {
  const url: string;
  export default url;
}

declare module '@host-tabs-bar' {
  import type { QueryTabsBarProps } from './query-tabs/query-tabs-bar';
  import type { ComponentType } from 'react';
  export const HostTabsBar: ComponentType<QueryTabsBarProps>;
}
