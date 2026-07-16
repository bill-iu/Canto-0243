import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  SESSION_KEY,
  VIEW,
  serializeSession,
  deserializeSession,
  createSearchTab,
  createGuideTab,
  createAboutTab,
  createRelationTab,
  createCorrectionsTab,
  applyUrlToTabs,
  openSingletonView,
  closeTab as closeTabReducer,
  reorderTab,
  reorderTabsByIds,
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
import { uiModeToUrlMode, urlModeToUiMode, type PingzeSubMode, type UiMode } from '../mode-meta';
import { stripLauncherBootFromUrl } from '../search-url';
import type { QueryResult } from '../db/query';
import {
  commitActiveSearchTransaction,
  openCommittedSearchTabTransaction,
} from '../../../frontend/committed-search.mjs';
import { isPortableHost } from '../host-mode';

export type { QueryTab, TabState };
export { tabLabel, VIEW };

/** PWA keeps search/guide/about only; portable host allows maintainer views. */
const PWA_VIEWS = new Set([VIEW.SEARCH, VIEW.GUIDE, VIEW.ABOUT]);

function sanitizePwaTabState(state: TabState): TabState {
  if (isPortableHost()) return state;
  const tabs = state.tabs.filter((t) => PWA_VIEWS.has(t.view));
  if (!tabs.length) {
    return { activeId: 1, nextTabId: 2, tabs: [createSearchTab({ id: 1 })] };
  }
  const activeId = tabs.some((t) => t.id === state.activeId) ? state.activeId : tabs[0].id;
  return { ...state, tabs, activeId };
}

export interface InitialTabBootstrap {
  isHome: boolean;
  forceLive: boolean;
}

function emptySearchSnapshot(tab: QueryTab): QueryTab {
  if (tab.view !== VIEW.SEARCH) return tab;
  return { ...tab, q: '', results: [], offset: 0, total: null };
}

function loadSessionTabState(): TabState | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) {
      return sanitizePwaTabState(deserializeSession(raw));
    }
  } catch {
    /* invalid session */
  }
  return null;
}

function loadInitialTabState(): { state: TabState; bootstrap: InitialTabBootstrap } {
  const fallback = (): TabState => ({
    activeId: 1,
    nextTabId: 2,
    tabs: [createSearchTab({ id: 1 })],
  });

  if (typeof window === 'undefined') {
    return { state: fallback(), bootstrap: { isHome: true, forceLive: false } };
  }

  const parsed = parseUrlSearchParams(new URLSearchParams(window.location.search));
  const urlHasQ = parsed.view === VIEW.SEARCH && Boolean(parsed.q?.trim());
  const isHome = parsed.view === VIEW.SEARCH && !parsed.q?.trim();

  let state = loadSessionTabState() ?? fallback();

  if (
    parsed.view === VIEW.GUIDE ||
    parsed.view === VIEW.ABOUT ||
    parsed.view === VIEW.RELATION ||
    parsed.view === VIEW.CORRECTIONS
  ) {
    // PWA sanitize drops relation/corrections; portable keeps them.
    if (
      !isPortableHost() &&
      (parsed.view === VIEW.RELATION || parsed.view === VIEW.CORRECTIONS)
    ) {
      return { state: sanitizePwaTabState(state), bootstrap: { isHome: true, forceLive: false } };
    }
    state = applyUrlToTabs(state, parsed);
    let urlTab = state.tabs.find((t) => t.view === parsed.view);
    if (!urlTab) {
      const create =
        parsed.view === VIEW.GUIDE
          ? createGuideTab
          : parsed.view === VIEW.ABOUT
            ? createAboutTab
            : parsed.view === VIEW.RELATION
              ? createRelationTab
              : createCorrectionsTab;
      state = openSingletonView(state, parsed.view, create);
      urlTab = state.tabs.find((t) => t.view === parsed.view) ?? undefined;
    }
    if (urlTab) {
      state = { ...state, activeId: urlTab.id };
    }
    return { state: sanitizePwaTabState(state), bootstrap: { isHome: false, forceLive: false } };
  }

  if (urlHasQ) {
    const searchTab =
      state.tabs.find((t) => t.id === state.activeId && t.view === VIEW.SEARCH) ||
      state.tabs.find((t) => t.view === VIEW.SEARCH) ||
      createSearchTab({ id: state.nextTabId });
    const tabs = state.tabs.some((t) => t.id === searchTab.id) ? state.tabs : [...state.tabs, searchTab];
    const nextTabId = state.tabs.some((t) => t.id === searchTab.id) ? state.nextTabId : state.nextTabId + 1;
    const cleared = emptySearchSnapshot({ ...searchTab, q: parsed.q! });
    const pzmode = (parsed.pzmode === 'm2' || parsed.pzmode === 'm3' ? parsed.pzmode : 'm1') as PingzeSubMode;
    resetSearchTabHistory(cleared, parsed.mode, pzmode);
    commitSearchHistoryFrame(cleared, { q: parsed.q!, mode: parsed.mode, pzmode });
    state = {
      activeId: cleared.id,
      nextTabId,
      tabs: tabs.map((t) => (t.id === cleared.id ? cleared : t)),
    };
    return { state: sanitizePwaTabState(state), bootstrap: { isHome: false, forceLive: true } };
  }

  if (isHome) {
    state = {
      ...state,
      tabs: state.tabs.map((t) => emptySearchSnapshot(t)),
    };
    const searchTab = state.tabs.find((t) => t.view === VIEW.SEARCH);
    if (searchTab) {
      state = { ...state, activeId: searchTab.id };
    }
    return { state: sanitizePwaTabState(state), bootstrap: { isHome: true, forceLive: false } };
  }

  return { state: sanitizePwaTabState(state), bootstrap: { isHome: false, forceLive: false } };
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
  pzmode: PingzeSubMode;
}

export interface SearchTabSnapshot {
  q: string;
  results: QueryResult[];
  offset: number;
  total: number | null;
}

export interface UseQueryTabsOptions {
  currentMode: UiMode;
  currentPzMode: PingzeSubMode;
  onModeChange: (mode: UiMode, pzmode?: PingzeSubMode) => void;
}

export function useQueryTabs({ currentMode, currentPzMode, onModeChange }: UseQueryTabsOptions) {
  const [initialLoad] = useState(loadInitialTabState);
  const [tabState, setTabState] = useState<TabState>(initialLoad.state);
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
        tabStateRef.current = next;
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
        ensureSearchTabHistory(tab, uiModeToUrlMode(currentMode), currentPzMode);
      }
      const urlMode =
        tab.view === VIEW.SEARCH
          ? currentSearchHistoryFrame(tab).mode
          : uiModeToUrlMode(currentMode);
      const pzmode = tab.view === VIEW.SEARCH ? currentSearchHistoryFrame(tab).pzmode : currentPzMode;
      const params = buildUrlSearchParams(tab, urlMode, pzmode);
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
    [currentMode, currentPzMode],
  );

  const patchSearchTab = useCallback(
    (tabId: number, snapshot: Partial<SearchTabSnapshot>) => {
      setAndPersist((prev) => {
        const tabs = prev.tabs.map((t) => {
          if (t.id !== tabId || t.view !== VIEW.SEARCH) return t;
          return {
            ...t,
            q: snapshot.q !== undefined ? snapshot.q : t.q,
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

  const patchActiveSearchTab = useCallback(
    (snapshot: Partial<SearchTabSnapshot>) => {
      patchSearchTab(tabStateRef.current.activeId, snapshot);
    },
    [patchSearchTab],
  );

  const selectTab = useCallback(
    (id: number) => {
      if (tabStateRef.current.activeId === id) return;
      const tab = tabStateRef.current.tabs.find((candidate) => candidate.id === id);
      if (tab?.view === VIEW.SEARCH) {
        const frame = currentSearchHistoryFrame(tab);
        const pzmode = (frame.pzmode === 'm2' || frame.pzmode === 'm3' ? frame.pzmode : 'm1') as PingzeSubMode;
        onModeChange(urlModeToUiMode(frame.mode), pzmode);
      }
      setAndPersist((prev) => ({ ...prev, activeId: id }));
    },
    [setAndPersist, onModeChange],
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

  /** Guide example / deep-link: new search tab with q (does not overwrite current tab). */
  const openSearchTabWithQuery = useCallback(
    (q: string, mode: UiMode, pzmode: PingzeSubMode) => {
      const transaction = openCommittedSearchTabTransaction(
        tabStateRef.current,
        { q: q.trim(), mode: uiModeToUrlMode(mode), pzmode },
        createSearchTab,
      );
      tabStateRef.current = transaction.state;
      persistTabs(transaction.state);
      setTabState(transaction.state);
      queueMicrotask(() => pushBrowserUrl(transaction.state, !transaction.pushed));
    },
    [persistTabs, pushBrowserUrl],
  );

  const closeTab = useCallback(
    (tabId: number) => {
      setAndPersist((prev) => closeTabReducer(prev, tabId));
    },
    [setAndPersist],
  );

  const reorderTabs = useCallback(
    (fromIndex: number, toIndex: number) => {
      setAndPersist((prev) => reorderTab(prev, fromIndex, toIndex));
    },
    [setAndPersist],
  );

  const reorderTabsByIdList = useCallback(
    (orderedIds: number[]) => {
      setAndPersist((prev) => reorderTabsByIds(prev, orderedIds));
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

  const openRelation = useCallback(() => {
    if (!isPortableHost()) return;
    setAndPersist((prev) => {
      const next = openSingletonView(prev, VIEW.RELATION, createRelationTab);
      const singleton = next.tabs.find((t) => t.view === VIEW.RELATION);
      return singleton ? { ...next, activeId: singleton.id } : next;
    });
  }, [setAndPersist]);

  const openCorrections = useCallback(() => {
    if (!isPortableHost()) return;
    setAndPersist((prev) => {
      const next = openSingletonView(prev, VIEW.CORRECTIONS, createCorrectionsTab);
      const singleton = next.tabs.find((t) => t.view === VIEW.CORRECTIONS);
      return singleton ? { ...next, activeId: singleton.id } : next;
    });
  }, [setAndPersist]);

  const patchActiveRelation = useCallback(
    (relation: Record<string, string>) => {
      setAndPersist((prev) => {
        const tabs = prev.tabs.map((t) => {
          if (t.id !== prev.activeId || t.view !== VIEW.RELATION) return t;
          return { ...t, relation: { ...relation } };
        });
        return { ...prev, tabs };
      });
    },
    [setAndPersist],
  );

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
      resetSearchTabHistory(active, uiModeToUrlMode(currentMode), currentPzMode);
      const next = {
        ...state,
        tabs: state.tabs.map((t) => (t.id === active.id ? active : t)),
      };
      queueMicrotask(() => pushBrowserUrl(next, true));
      return next;
    });
  }, [currentMode, currentPzMode, setAndPersist, pushBrowserUrl]);

  const commitActiveSearch = useCallback(
    (q: string, mode: UiMode, pzmode: PingzeSubMode) => {
      const transaction = commitActiveSearchTransaction(tabStateRef.current, {
        q,
        mode: uiModeToUrlMode(mode),
        pzmode,
      });
      tabStateRef.current = transaction.state;
      persistTabs(transaction.state);
      setTabState(transaction.state);
      queueMicrotask(() => pushBrowserUrl(transaction.state, !transaction.pushed));
    },
    [persistTabs, pushBrowserUrl],
  );

  const consumePopstateFrame = useCallback(() => {
    setPopstateFrame(null);
  }, []);

  useEffect(() => {
    tabState.tabs.forEach((t) => {
      if (t.view === VIEW.SEARCH) {
        ensureSearchTabHistory(t, uiModeToUrlMode(currentMode), currentPzMode);
      }
    });
  }, [tabState.tabs, currentMode, currentPzMode]);

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
      const nextPzMode = (frame.pzmode === 'm2' || frame.pzmode === 'm3' ? frame.pzmode : 'm1') as PingzeSubMode;
      onModeChange(nextMode, nextPzMode);
      setAndPersist((prev) => ({
        ...prev,
        tabs: prev.tabs.map((t) => (t.id === tab.id ? tab : t)),
      }));
      pushBrowserUrl(tabStateRef.current, true);

      if (frame.q) {
        setPopstateFrame({ q: frame.q, mode: nextMode, pzmode: nextPzMode });
      } else {
        tab.results = [];
        tab.offset = 0;
        tab.total = null;
        setAndPersist((prev) => ({
          ...prev,
          tabs: prev.tabs.map((t) => (t.id === tab.id ? tab : t)),
        }));
        setPopstateFrame({ q: '', mode: nextMode, pzmode: nextPzMode });
      }
    };

    window.addEventListener('popstate', onPopstate);
    return () => window.removeEventListener('popstate', onPopstate);
  }, [setAndPersist, pushBrowserUrl, onModeChange]);

  const needsInitialSearch =
    activeTab?.view === VIEW.SEARCH &&
    Boolean((activeTab.q || '').trim()) &&
    (initialLoad.bootstrap.forceLive || !(activeTab.results as QueryResult[])?.length);

  return {
    initialBootstrap: initialLoad.bootstrap,
    tabState,
    activeTab,
    tabs: tabState.tabs,
    selectTab,
    addSearchTab,
    openSearchTabWithQuery,
    closeTab,
    reorderTabs,
    reorderTabsByIdList,
    openGuide,
    openAbout,
    openRelation,
    openCorrections,
    patchActiveRelation,
    goHome,
    ensureActiveSearchTab,
    patchActiveSearchTab,
    patchSearchTab,
    commitActiveSearch,
    pushBrowserUrl,
    popstateFrame,
    consumePopstateFrame,
    needsInitialSearch,
  };
}
