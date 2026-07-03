import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  SESSION_KEY,
  VIEW,
  serializeSession,
  deserializeSession,
  createSearchTab,
  createGuideTab,
  createAboutTab,
  applyUrlToTabs,
  openSingletonView,
  closeTab as closeTabReducer,
  parseUrlSearchParams,
  buildUrlSearchParams,
  tabLabel,
  type QueryTab,
  type TabState,
} from '@shared/query-tabs';
import {
  buildHistoryStateForTab,
  commitSearchHistoryFrame,
  currentSearchHistoryFrame,
  ensureSearchTabHistory,
  isHistoryForward,
  resetSearchTabHistory,
  shouldPushSearchHistory,
  stepSearchTabBack,
} from '@shared/search-navigation';
import { uiModeToUrlMode, urlModeToUiMode, type UiMode } from '../mode-meta';
import { stripLauncherBootFromUrl } from '../search-url';
import type { QueryResult } from '../db/query';

export type { QueryTab, TabState };
export { tabLabel, VIEW };

const PWA_VIEWS = new Set([VIEW.SEARCH, VIEW.GUIDE, VIEW.ABOUT]);

function sanitizePwaTabState(state: TabState): TabState {
  const tabs = state.tabs.filter((t) => PWA_VIEWS.has(t.view));
  if (!tabs.length) {
    return { activeId: 1, nextTabId: 2, tabs: [createSearchTab({ id: 1 })] };
  }
  const activeId = tabs.some((t) => t.id === state.activeId) ? state.activeId : tabs[0].id;
  return { ...state, tabs, activeId };
}

function loadInitialTabState(): TabState {
  if (typeof window === 'undefined') {
    return { activeId: 1, nextTabId: 2, tabs: [createSearchTab({ id: 1 })] };
  }
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) {
      return sanitizePwaTabState(deserializeSession(raw));
    }
  } catch {
    /* invalid session */
  }
  const parsed = parseUrlSearchParams(new URLSearchParams(window.location.search));
  let state = applyUrlToTabs(null, parsed);
  if (!state.tabs.length) {
    state = { activeId: 1, nextTabId: 2, tabs: [createSearchTab({ id: 1 })] };
  }
  const urlTab = state.tabs.find((t) => {
    if (parsed.view === VIEW.GUIDE) return t.view === VIEW.GUIDE;
    if (parsed.view === VIEW.ABOUT) return t.view === VIEW.ABOUT;
    return t.view === VIEW.SEARCH;
  });
  if (urlTab) {
    state = { ...state, activeId: urlTab.id };
  }
  if (parsed.view === VIEW.SEARCH && parsed.q) {
    const searchTab =
      state.tabs.find((t) => t.id === state.activeId && t.view === VIEW.SEARCH) ||
      state.tabs.find((t) => t.view === VIEW.SEARCH);
    if (searchTab) {
      searchTab.q = parsed.q;
      state = { ...state, activeId: searchTab.id };
    }
  }
  return sanitizePwaTabState(state);
}

function historySeqFromState(state: unknown): number {
  const n = (state as { _histSeq?: number } | null)?._histSeq;
  return typeof n === 'number' ? n : 0;
}

function firstSearchTab(state: TabState): QueryTab | null {
  return state.tabs.find((t) => t.view === VIEW.SEARCH) ?? null;
}

export interface PopstateSearchFrame {
  q: string;
  mode: UiMode;
}

export interface SearchTabSnapshot {
  q: string;
  results: QueryResult[];
  offset: number;
  total: number | null;
}

export interface UseQueryTabsOptions {
  currentMode: UiMode;
  onModeChange: (mode: UiMode) => void;
}

export function useQueryTabs({ currentMode, onModeChange }: UseQueryTabsOptions) {
  const [tabState, setTabState] = useState<TabState>(loadInitialTabState);
  const [popstateFrame, setPopstateFrame] = useState<PopstateSearchFrame | null>(null);
  const tabStateRef = useRef(tabState);
  tabStateRef.current = tabState;
  const lastHistSeqRef = useRef(
    typeof window !== 'undefined' ? historySeqFromState(window.history.state) : 0,
  );
  const nextHistSeqRef = useRef(1);
  const suppressPopstateRef = useRef(false);
  const initDoneRef = useRef(false);

  const activeTab = useMemo(
    () => tabState.tabs.find((t) => t.id === tabState.activeId) ?? tabState.tabs[0] ?? null,
    [tabState],
  );

  const persistTabs = useCallback((state: TabState) => {
    try {
      sessionStorage.setItem(SESSION_KEY, serializeSession(state));
    } catch {
      /* quota */
    }
  }, []);

  const setAndPersist = useCallback(
    (updater: TabState | ((prev: TabState) => TabState)) => {
      setTabState((prev) => {
        const next = typeof updater === 'function' ? updater(prev) : updater;
        persistTabs(next);
        return next;
      });
    },
    [persistTabs],
  );

  const pushBrowserUrl = useCallback(
    (state: TabState, replace = false) => {
      if (typeof window === 'undefined') return;
      const tab = state.tabs.find((t) => t.id === state.activeId) ?? state.tabs[0];
      if (!tab) return;
      if (tab.view === VIEW.SEARCH) {
        ensureSearchTabHistory(tab, uiModeToUrlMode(currentMode));
      }
      const urlMode =
        tab.view === VIEW.SEARCH
          ? currentSearchHistoryFrame(tab).mode
          : uiModeToUrlMode(currentMode);
      const params = buildUrlSearchParams(tab, urlMode);
      const suffix = params.toString() ? `?${params.toString()}` : '';
      const url = `${window.location.pathname}${suffix}`;
      const histState = buildHistoryStateForTab(tab, urlMode) as ReturnType<
        typeof buildHistoryStateForTab
      > & { _histSeq?: number };
      const prevState = window.history.state;
      const useReplace = replace || !shouldPushSearchHistory(histState, prevState);
      if (useReplace) {
        histState._histSeq = historySeqFromState(prevState) || lastHistSeqRef.current || nextHistSeqRef.current++;
      } else {
        histState._histSeq = nextHistSeqRef.current++;
      }
      if (useReplace) {
        window.history.replaceState(histState, '', url);
      } else {
        window.history.pushState(histState, '', url);
      }
      lastHistSeqRef.current = histState._histSeq;
    },
    [currentMode],
  );

  const patchActiveSearchTab = useCallback(
    (snapshot: Partial<SearchTabSnapshot>) => {
      setAndPersist((prev) => {
        const tabs = prev.tabs.map((t) => {
          if (t.id !== prev.activeId || t.view !== VIEW.SEARCH) return t;
          return {
            ...t,
            q: snapshot.q ?? t.q,
            results: snapshot.results ?? (t.results as QueryResult[]),
            offset: snapshot.offset ?? t.offset,
            total: snapshot.total !== undefined ? snapshot.total : t.total,
          };
        });
        return { ...prev, tabs };
      });
    },
    [setAndPersist],
  );

  const selectTab = useCallback(
    (id: number) => {
      if (tabStateRef.current.activeId === id) return;
      setAndPersist((prev) => ({ ...prev, activeId: id }));
    },
    [setAndPersist],
  );

  const addSearchTab = useCallback(() => {
    setAndPersist((prev) => {
      const tab = createSearchTab({ id: prev.nextTabId });
      const next = {
        activeId: tab.id,
        nextTabId: prev.nextTabId + 1,
        tabs: [...prev.tabs, tab],
      };
      return next;
    });
  }, [setAndPersist]);

  const closeTab = useCallback(
    (tabId: number) => {
      setAndPersist((prev) => closeTabReducer(prev, tabId));
    },
    [setAndPersist],
  );

  const openGuide = useCallback(() => {
    setAndPersist((prev) => {
      const next = openSingletonView(prev, VIEW.GUIDE, createGuideTab);
      const singleton = next.tabs.find((t) => t.view === VIEW.GUIDE);
      return singleton ? { ...next, activeId: singleton.id } : next;
    });
  }, [setAndPersist]);

  const openAbout = useCallback(() => {
    setAndPersist((prev) => {
      const next = openSingletonView(prev, VIEW.ABOUT, createAboutTab);
      const singleton = next.tabs.find((t) => t.view === VIEW.ABOUT);
      return singleton ? { ...next, activeId: singleton.id } : next;
    });
  }, [setAndPersist]);

  const ensureActiveSearchTab = useCallback(() => {
    let picked: QueryTab | null = null;
    setAndPersist((prev) => {
      const current = prev.tabs.find((t) => t.id === prev.activeId);
      if (current?.view === VIEW.SEARCH) {
        picked = current;
        return prev;
      }
      const existing = firstSearchTab(prev);
      if (existing) {
        picked = existing;
        return { ...prev, activeId: existing.id };
      }
      const tab = createSearchTab({ id: prev.nextTabId });
      picked = tab;
      return {
        activeId: tab.id,
        nextTabId: prev.nextTabId + 1,
        tabs: [...prev.tabs, tab],
      };
    });
    return picked;
  }, [setAndPersist]);

  const goHome = useCallback(() => {
    setAndPersist((prev) => {
      let state = prev;
      const current = state.tabs.find((t) => t.id === state.activeId);
      if (current?.view !== VIEW.SEARCH) {
        let searchTab = firstSearchTab(state);
        if (!searchTab) {
          searchTab = createSearchTab({ id: state.nextTabId });
          state = {
            activeId: searchTab.id,
            nextTabId: state.nextTabId + 1,
            tabs: [...state.tabs, searchTab],
          };
        } else {
          state = { ...state, activeId: searchTab.id };
        }
      }
      const active = state.tabs.find((t) => t.id === state.activeId);
      if (!active || active.view !== VIEW.SEARCH) return state;
      resetSearchTabHistory(active, uiModeToUrlMode(currentMode));
      const next = {
        ...state,
        tabs: state.tabs.map((t) => (t.id === active.id ? active : t)),
      };
      queueMicrotask(() => pushBrowserUrl(next, true));
      return next;
    });
  }, [currentMode, setAndPersist, pushBrowserUrl]);

  const commitActiveSearch = useCallback(
    (q: string, mode: UiMode) => {
      const urlMode = uiModeToUrlMode(mode);
      let pushed = false;
      setAndPersist((prev) => {
        const tabs = prev.tabs.map((t) => {
          if (t.id !== prev.activeId || t.view !== VIEW.SEARCH) return t;
          const result = commitSearchHistoryFrame(t, { q, mode: urlMode });
          pushed = result.pushed;
          return t;
        });
        return { ...prev, tabs };
      });
      return pushed;
    },
    [setAndPersist],
  );

  const consumePopstateFrame = useCallback(() => {
    setPopstateFrame(null);
  }, []);

  useEffect(() => {
    tabState.tabs.forEach((t) => {
      if (t.view === VIEW.SEARCH) {
        ensureSearchTabHistory(t, uiModeToUrlMode(currentMode));
      }
    });
  }, [tabState.tabs, currentMode]);

  useEffect(() => {
    if (initDoneRef.current) return;
    initDoneRef.current = true;
    stripLauncherBootFromUrl();
    pushBrowserUrl(tabStateRef.current, true);
    persistTabs(tabStateRef.current);
  }, [pushBrowserUrl, persistTabs]);

  useEffect(() => {
    if (!initDoneRef.current) return;
    pushBrowserUrl(tabStateRef.current, true);
  }, [tabState.activeId, pushBrowserUrl]);

  useEffect(() => {
    const onPopstate = (event: PopStateEvent) => {
      const state = event.state || {};
      const current = tabStateRef.current;
      const tab = current.tabs.find((t) => t.id === current.activeId) ?? current.tabs[0];
      const seq = state._histSeq;

      if (tab?.view !== VIEW.SEARCH) {
        if (typeof seq === 'number') lastHistSeqRef.current = seq;
        pushBrowserUrl(current, true);
        return;
      }

      if (suppressPopstateRef.current) {
        suppressPopstateRef.current = false;
        if (typeof seq === 'number') lastHistSeqRef.current = seq;
        pushBrowserUrl(current, true);
        return;
      }

      if (isHistoryForward(lastHistSeqRef.current, state)) {
        suppressPopstateRef.current = true;
        window.history.back();
        return;
      }

      if (typeof seq === 'number') lastHistSeqRef.current = seq;

      const frame = stepSearchTabBack(tab);
      if (!frame) {
        suppressPopstateRef.current = true;
        window.history.forward();
        pushBrowserUrl(current, true);
        return;
      }

      const nextMode = urlModeToUiMode(frame.mode);
      onModeChange(nextMode);
      setAndPersist((prev) => ({
        ...prev,
        tabs: prev.tabs.map((t) => (t.id === tab.id ? tab : t)),
      }));
      pushBrowserUrl(tabStateRef.current, true);

      if (frame.q) {
        setPopstateFrame({ q: frame.q, mode: nextMode });
      } else {
        tab.results = [];
        tab.offset = 0;
        tab.total = null;
        setAndPersist((prev) => ({
          ...prev,
          tabs: prev.tabs.map((t) => (t.id === tab.id ? tab : t)),
        }));
        setPopstateFrame({ q: '', mode: nextMode });
      }
    };

    window.addEventListener('popstate', onPopstate);
    return () => window.removeEventListener('popstate', onPopstate);
  }, [setAndPersist, pushBrowserUrl, onModeChange]);

  const needsInitialSearch =
    activeTab?.view === VIEW.SEARCH &&
    Boolean((activeTab.q || '').trim()) &&
    !(activeTab.results as QueryResult[])?.length;

  return {
    tabState,
    activeTab,
    tabs: tabState.tabs,
    selectTab,
    addSearchTab,
    closeTab,
    openGuide,
    openAbout,
    goHome,
    ensureActiveSearchTab,
    patchActiveSearchTab,
    commitActiveSearch,
    pushBrowserUrl,
    popstateFrame,
    consumePopstateFrame,
    needsInitialSearch,
  };
}
