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

  export function tabLabel(tab: QueryTab): string;
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
