import { getQueryTabCopy } from './query-tabs-i18n.mjs';

export const SESSION_KEY = "canto0243:query-tabs";
export const TAB_LABEL_MAX = 18;

export const VIEW = Object.freeze({
  SEARCH: "search",
  WORKBENCH: "workbench",
  GUIDE: "guide",
  RELATION: "relation",
  CORRECTIONS: "corrections",
  ABOUT: "about",
});

export function tabLabel(tab, lang = "zh") {
  const copy = getQueryTabCopy(lang);
  if (tab.view === VIEW.WORKBENCH) return copy.workbench;
  if (tab.view === VIEW.GUIDE) return copy.guide;
  if (tab.view === VIEW.ABOUT) return copy.about;
  if (tab.view === VIEW.RELATION) return copy.relation;
  if (tab.view === VIEW.CORRECTIONS) return copy.corrections;
  const q = (tab.q || "").trim();
  if (!q) return copy.newQuery;
  return q.length > TAB_LABEL_MAX ? `${q.slice(0, TAB_LABEL_MAX)}…` : q;
}

export function findTabByView(tabs, view) {
  return tabs.find((t) => t.view === view) || null;
}

export function createSearchTab({
  id,
  q = "",
  results = [],
  offset = 0,
  total = null,
  mode = "m1",
  pzmode = "m1",
  shuffled = false,
  scrollTop = 0,
  dataVersion = null,
  posFilter = null,
  historyStack = null,
  historyIndex = 0,
} = {}) {
  const stack = historyStack ?? [{ q: "", mode: "m1" }];
  const index = typeof historyIndex === "number" ? historyIndex : stack.length - 1;
  return {
    id,
    view: VIEW.SEARCH,
    q,
    results,
    offset,
    total,
    mode,
    pzmode,
    shuffled: Boolean(shuffled),
    scrollTop: Number.isFinite(scrollTop) ? Math.max(0, scrollTop) : 0,
    dataVersion: typeof dataVersion === "string" ? dataVersion : null,
    posFilter: posFilter && typeof posFilter === "object" ? {
      pos: Array.isArray(posFilter.pos) ? [...posFilter.pos] : [],
      family: Array.isArray(posFilter.family) ? [...posFilter.family] : [],
      voice: Array.isArray(posFilter.voice) ? [...posFilter.voice] : [],
    } : { pos: [], family: [], voice: [] },
    historyStack: stack,
    historyIndex: index,
  };
}

export function createWorkbenchTab({ id } = {}) {
  return {
    id,
    view: VIEW.WORKBENCH,
    q: "",
    results: [],
    offset: 0,
    total: null,
  };
}

export function createGuideTab({ id } = {}) {
  return {
    id,
    view: VIEW.GUIDE,
    q: "",
    results: [],
    offset: 0,
    total: null,
  };
}

export function createRelationTab({ id, relation = { seed_char: "", opposite_char: "", relation_type: "syn" } } = {}) {
  return {
    id,
    view: VIEW.RELATION,
    q: "",
    results: [],
    offset: 0,
    total: null,
    relation: { ...relation },
  };
}

export function createCorrectionsTab({ id, prefetchChar = "" } = {}) {
  return {
    id,
    view: VIEW.CORRECTIONS,
    q: "",
    results: [],
    offset: 0,
    total: null,
    prefetchChar: prefetchChar || "",
  };
}

export function createAboutTab({ id } = {}) {
  return {
    id,
    view: VIEW.ABOUT,
    q: "",
    results: [],
    offset: 0,
    total: null,
  };
}

/** ponytail: maintainer 入口；builder 輸入 debug 開勘誤分頁，唔當查詢。 */
export function isCorrectionsSearchCommand(q) {
  return (q || "").trim().toLowerCase() === "debug";
}

export function openSingletonView(state, view, createTab) {
  const existing = findTabByView(state.tabs, view);
  if (existing) {
    return { ...state, activeId: existing.id };
  }
  const tab = createTab({ id: state.nextTabId });
  return {
    activeId: tab.id,
    nextTabId: state.nextTabId + 1,
    tabs: [...state.tabs, tab],
  };
}

export function buildUrlSearchParams(tab, mode = "m1", pzmode = "m1") {
  const params = new URLSearchParams();
  if (mode && mode !== "m1") params.set("mode", mode);
  if (mode === "pz") params.set("pzmode", ["m1", "m2", "m3"].includes(pzmode) ? pzmode : "m1");
  if (tab.view === VIEW.WORKBENCH) {
    params.set("view", "workbench");
    return params;
  }
  if (tab.view === VIEW.GUIDE) {
    params.set("view", "guide");
    return params;
  }
  if (tab.view === VIEW.RELATION) {
    params.set("view", "relation");
    return params;
  }
  if (tab.view === VIEW.CORRECTIONS) {
    params.set("view", "corrections");
    return params;
  }
  if (tab.view === VIEW.ABOUT) {
    params.set("view", "about");
    return params;
  }
  if (tab.q) params.set("q", tab.q);
  return params;
}

export function parseUrlSearchParams(params) {
  const rawView = params.get("view");
  let view = VIEW.SEARCH;
  if (rawView === "guide") view = VIEW.GUIDE;
  else if (rawView === "workbench") view = VIEW.WORKBENCH;
  else if (rawView === "relation") view = VIEW.RELATION;
  else if (rawView === "corrections") view = VIEW.CORRECTIONS;
  else if (rawView === "about") view = VIEW.ABOUT;
  return {
    q: params.get("q") || "",
    mode: params.get("mode") || "m1",
    pzmode: ["m1", "m2", "m3"].includes(params.get("pzmode")) ? params.get("pzmode") : "m1",
    view,
  };
}

/** local_launch cache-bust only — not a semantic query param. */
export const LAUNCHER_BOOT_PARAM = "boot";

export function searchParamsWithoutBoot(params) {
  if (!params.has(LAUNCHER_BOOT_PARAM)) return null;
  const next = new URLSearchParams(params);
  next.delete(LAUNCHER_BOOT_PARAM);
  return next;
}

export function serializeSession(state) {
  return JSON.stringify({
    activeId: state.activeId,
    nextTabId: state.nextTabId,
    tabs: state.tabs.map((t) => ({
      id: t.id,
      view: t.view,
      q: t.q,
      offset: t.offset,
      total: t.total,
      historyStack: t.view === VIEW.SEARCH ? t.historyStack : undefined,
      historyIndex: t.view === VIEW.SEARCH ? t.historyIndex : undefined,
      posFilter: t.view === VIEW.SEARCH ? t.posFilter : undefined,
      relation: t.relation ? { ...t.relation } : undefined,
      prefetchChar: t.prefetchChar || "",
    })),
  });
}

export function deserializeSession(raw) {
  const data = JSON.parse(raw);
  if (!Array.isArray(data.tabs) || !data.tabs.length) {
    throw new Error("invalid session");
  }
  return {
    activeId: data.activeId || data.tabs[0].id,
    nextTabId: data.nextTabId || Math.max(...data.tabs.map((t) => t.id)) + 1,
    tabs: data.tabs.map((t) => {
      if (t.view === VIEW.GUIDE) return createGuideTab({ id: t.id });
      if (t.view === VIEW.WORKBENCH) return createWorkbenchTab({ id: t.id });
      if (t.view === VIEW.RELATION) {
        return createRelationTab({ id: t.id, relation: t.relation });
      }
      if (t.view === VIEW.CORRECTIONS) {
        return createCorrectionsTab({ id: t.id, prefetchChar: t.prefetchChar });
      }
      if (t.view === VIEW.ABOUT) return createAboutTab({ id: t.id });
      return createSearchTab({
        id: t.id,
        q: t.q || "",
        results: t.results || [],
        offset: t.offset || 0,
        total: t.total ?? null,
        mode: typeof t.mode === "string" ? t.mode : "m1",
        pzmode: typeof t.pzmode === "string" ? t.pzmode : "m1",
        shuffled: Boolean(t.shuffled),
        scrollTop: Number.isFinite(t.scrollTop) ? t.scrollTop : 0,
        dataVersion: typeof t.dataVersion === "string" ? t.dataVersion : null,
        historyStack: Array.isArray(t.historyStack) ? t.historyStack : null,
        historyIndex: t.historyIndex,
        posFilter: t.posFilter,
      });
    }),
  };
}

export function closeTab(state, tabId) {
  if (state.tabs.length <= 1) return state;
  const idx = state.tabs.findIndex((t) => t.id === tabId);
  const tabs = state.tabs.filter((t) => t.id !== tabId);
  let activeId = state.activeId;
  if (activeId === tabId) {
    const pick = tabs[Math.max(0, idx - 1)];
    activeId = pick.id;
  }
  return { ...state, tabs, activeId };
}

export function reorderTab(state, fromIndex, toIndex) {
  const { tabs } = state;
  if (fromIndex === toIndex) return state;
  if (fromIndex < 0 || fromIndex >= tabs.length) return state;
  if (toIndex < 0 || toIndex >= tabs.length) return state;
  const next = [...tabs];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return { ...state, tabs: next };
}

export function reorderTabsByIds(state, orderedIds) {
  const byId = new Map(state.tabs.map((t) => [t.id, t]));
  const tabs = orderedIds.map((id) => byId.get(id)).filter((t) => t != null);
  if (tabs.length !== state.tabs.length) return state;
  const unchanged = state.tabs.every((t, i) => t.id === tabs[i].id);
  if (unchanged) return state;
  return { ...state, tabs };
}

export function applyUrlToTabs(existingState, parsed) {
  if (existingState) {
    return existingState;
  }
  if (parsed.view === VIEW.GUIDE) {
    const tab = createGuideTab({ id: 1 });
    return { activeId: 1, nextTabId: 2, tabs: [tab] };
  }
  if (parsed.view === VIEW.WORKBENCH) {
    const tab = createWorkbenchTab({ id: 1 });
    return { activeId: 1, nextTabId: 2, tabs: [tab] };
  }
  if (parsed.view === VIEW.RELATION) {
    const tab = createRelationTab({ id: 1 });
    return { activeId: 1, nextTabId: 2, tabs: [tab] };
  }
  if (parsed.view === VIEW.CORRECTIONS) {
    const tab = createCorrectionsTab({ id: 1 });
    return { activeId: 1, nextTabId: 2, tabs: [tab] };
  }
  if (parsed.view === VIEW.ABOUT) {
    const tab = createAboutTab({ id: 1 });
    return { activeId: 1, nextTabId: 2, tabs: [tab] };
  }
  const tab = createSearchTab({ id: 1, q: parsed.q });
  return { activeId: 1, nextTabId: 2, tabs: [tab] };
}
