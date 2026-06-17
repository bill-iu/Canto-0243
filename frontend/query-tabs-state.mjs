export const SESSION_KEY = "canto0243:query-tabs";
export const TAB_LABEL_MAX = 18;

export const VIEW = Object.freeze({
  SEARCH: "search",
  GUIDE: "guide",
  RELATION: "relation",
});

export function tabLabel(tab) {
  if (tab.view === VIEW.GUIDE) return "搜尋教學";
  if (tab.view === VIEW.RELATION) return "補關係";
  const q = (tab.q || "").trim();
  if (!q) return "新查詢";
  return q.length > TAB_LABEL_MAX ? `${q.slice(0, TAB_LABEL_MAX)}…` : q;
}

export function findTabByView(tabs, view) {
  return tabs.find((t) => t.view === view) || null;
}

export function createSearchTab({ id, q = "", results = [], offset = 0, total = null } = {}) {
  return {
    id,
    view: VIEW.SEARCH,
    q,
    results,
    offset,
    total,
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

export function buildUrlSearchParams(tab, mode = "m1") {
  const params = new URLSearchParams();
  if (mode && mode !== "m1") params.set("mode", mode);
  if (tab.view === VIEW.GUIDE) {
    params.set("view", "guide");
    return params;
  }
  if (tab.view === VIEW.RELATION) {
    params.set("view", "relation");
    return params;
  }
  if (tab.q) params.set("q", tab.q);
  return params;
}

export function parseUrlSearchParams(params) {
  const rawView = params.get("view");
  let view = VIEW.SEARCH;
  if (rawView === "guide") view = VIEW.GUIDE;
  else if (rawView === "relation") view = VIEW.RELATION;
  return {
    q: params.get("q") || "",
    mode: params.get("mode") || "m1",
    view,
  };
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
      relation: t.relation ? { ...t.relation } : undefined,
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
      if (t.view === VIEW.RELATION) {
        return createRelationTab({ id: t.id, relation: t.relation });
      }
      return createSearchTab({
        id: t.id,
        q: t.q || "",
        results: t.results || [],
        offset: t.offset || 0,
        total: t.total ?? null,
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
  if (parsed.view === VIEW.RELATION) {
    const tab = createRelationTab({ id: 1 });
    return { activeId: 1, nextTabId: 2, tabs: [tab] };
  }
  const tab = createSearchTab({ id: 1, q: parsed.q });
  return { activeId: 1, nextTabId: 2, tabs: [tab] };
}
