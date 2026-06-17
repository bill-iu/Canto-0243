import { escapeHtmlAttr } from "./dom-escape.mjs";
import {
  $,
  VIEW,
  TAB_GEOMETRY_SVG,
  tabState,
  chromeLayout,
  pendingNewTabAnimation,
  createSearchTab,
  createGuideTab,
  createRelationTab,
  findTabByView,
  openSingletonView,
  reorderTabsByIds,
  closeTabInState,
  tabLabel,
} from "./app-context.mjs";
import {
  activeTab, firstSearchTab, persistTabs, saveActiveTabFromUi,
  updateBrowserUrlFromActiveTab, markActiveTabInStrip, animateNewTabEntry,
  updateTabstripLastMarkers, scrollActiveTabIntoView,
} from "./tabs-core.mjs";
import { syncViewPanels } from "./view-sync.mjs";
import {
  toggleLoadMoreButton, updateShuffleButton, toggleMenu,
} from "./search-workbench.mjs";

function renderTabstrip() {
  const tabsHtml = tabState.tabs
    .map((t, idx) => {
      const isActive = t.id === tabState.activeId;
      const isLast = idx === tabState.tabs.length - 1;
      const closeBtn =
        tabState.tabs.length > 1
          ? `<button type="button" class="chrome-tab-close" data-close="${t.id}" aria-label="關閉分頁"></button>`
          : "";
      const label = tabLabel(t);
      return `
        <div class="chrome-tab${isLast ? " chrome-tab-is-last" : ""}" data-tab-id="${t.id}"${isActive ? " active" : ""} role="presentation">
          <div class="chrome-tab-dividers"></div>
          <div class="chrome-tab-background">${TAB_GEOMETRY_SVG}</div>
          <div class="chrome-tab-content">
            <div class="chrome-tab-favicon" hidden></div>
            <div class="chrome-tab-title">${escapeHtmlAttr(label)}</div>
            <div class="chrome-tab-drag-handle" role="tab" aria-selected="${isActive}" aria-label="${escapeHtmlAttr(label)}" data-tab="${t.id}"></div>
            ${closeBtn}
          </div>
        </div>`;
    })
    .join("");
  $.tabstrip.innerHTML =
    tabsHtml +
    `<div class="chrome-tab chrome-tab-add" role="presentation" data-add-tab>
      <div class="chrome-tab-add-hit" role="button" aria-label="新查詢分頁" title="Alt+N">+</div>
    </div>`;
  wireTabstrip();
  if (chromeLayout) {
    chromeLayout.layout();
    setupTabDrag();
  }
  if (pendingNewTabAnimation) {
    const { tabId } = pendingNewTabAnimation;
    pendingNewTabAnimation = null;
    animateNewTabEntry(tabId);
  }
  requestAnimationFrame(scrollActiveTabIntoView);
}

function setupTabDrag() {
  if (!chromeLayout || typeof Draggabilly === "undefined") return;
  chromeLayout.setupDraggabilly({
    onPointerDown(id) {
      activateTabOnPress(id);
    },
    onReorderEnd(orderedIds) {
      const next = reorderTabsByIds(tabState, orderedIds);
      if (next === tabState) return;
      tabState = next;
      persistTabs();
      updateTabstripLastMarkers();
    },
  });
}

function wireTabstrip() {
  $.tabstrip.querySelectorAll("[data-tab]").forEach((el) => {
    el.addEventListener("click", () => selectTab(Number(el.dataset.tab)));
    el.addEventListener("auxclick", (e) => {
      if (e.button !== 1) return;
      e.preventDefault();
      closeTab(Number(el.dataset.tab));
    });
  });
  $.tabstrip.querySelectorAll("[data-add-tab]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      addSearchTab();
    });
  });
  $.tabstrip.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      closeTab(Number(btn.dataset.close));
    });
  });
  wireTabstripHoverDividers();
}

function wireTabstripHoverDividers() {
  const clearHoverFlags = () => {
    $.tabstrip.querySelectorAll(".chrome-tab").forEach((t) => {
      t.classList.remove("is-hovered", "hide-left-divider-hover", "hide-right-divider-hover");
    });
    applyActiveNeighborDividerHides();
  };
  $.tabstrip.querySelectorAll(".chrome-tab:not(.chrome-tab-add)").forEach((tab) => {
    tab.addEventListener("mouseenter", () => {
      clearHoverFlags();
      tab.classList.add("is-hovered");
      const prev = tab.previousElementSibling;
      const next = tab.nextElementSibling;
      if (prev && prev.classList.contains("chrome-tab") && !prev.classList.contains("chrome-tab-add")) {
        prev.classList.add("hide-right-divider-hover");
      }
      if (next && next.classList.contains("chrome-tab") && !next.classList.contains("chrome-tab-add")) {
        next.classList.add("hide-left-divider-hover");
      }
    });
    tab.addEventListener("mouseleave", clearHoverFlags);
  });
  applyActiveNeighborDividerHides();
}

function activateTabOnPress(id) {
  if (tabState.activeId === id) return;
  saveActiveTabFromUi();
  tabState = { ...tabState, activeId: id };
  persistTabs();
  markActiveTabInStrip(id);
  syncViewPanels({ renderTabstrip: false });
  const tab = activeTab();
  if (tab?.view === VIEW.SEARCH) $.searchInput.focus();
  else if (tab?.view === VIEW.GUIDE) document.getElementById("guideTitle")?.focus({ preventScroll: true });
  else if (tab?.view === VIEW.RELATION) $.seedChar?.focus({ preventScroll: true });
}

function addSearchTab() {
  saveActiveTabFromUi();
  const tab = createSearchTab({ id: tabState.nextTabId });
  pendingNewTabAnimation = { tabId: tab.id };
  tabState = {
    activeId: tab.id,
    nextTabId: tabState.nextTabId + 1,
    tabs: [...tabState.tabs, tab],
  };
  persistTabs();
  syncViewPanels();
  if (activeTab()?.view === VIEW.SEARCH) $.searchInput.focus();
}

function closeTab(id) {
  if (tabState.tabs.length <= 1) return;
  saveActiveTabFromUi();
  tabState = closeTabInState(tabState, id);
  persistTabs();
  syncViewPanels();
}

function selectTab(id) {
  if (tabState.activeId === id) return;
  saveActiveTabFromUi();
  tabState = { ...tabState, activeId: id };
  persistTabs();
  syncViewPanels();
  const tab = activeTab();
  if (tab?.view === VIEW.SEARCH) $.searchInput.focus();
  else if (tab?.view === VIEW.GUIDE) document.getElementById("guideTitle")?.focus({ preventScroll: true });
  else if (tab?.view === VIEW.RELATION) $.seedChar?.focus({ preventScroll: true });
}

function openSingletonViewTab(view, createTab) {
  saveActiveTabFromUi();
  tabState = openSingletonView(tabState, view, createTab);
  const singleton = findTabByView(tabState.tabs, view);
  if (singleton) tabState = { ...tabState, activeId: singleton.id };
  persistTabs();
  syncViewPanels();
  toggleMenu(false);
  if (view === VIEW.GUIDE) {
    document.getElementById("guideTitle")?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (view === VIEW.RELATION) {
    $.seedChar?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

const LANDING_VARIANT = document.documentElement.dataset.landing || "a";
const LANDING_SESSION_KEY = "canto0243:landing-done";
const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const LANDING_REVEAL_MS = 420;
const LANDING_HANDOFF_MS = 640;
const GATE_BRAND_INTRO_MS = 700;

const GATE_NEAR_DONE_PCT = 85;
const GATE_INK_CLIP_MAX = 200;

function focusSearchTab(tab) {
  if (!tab || tab.view !== VIEW.SEARCH) return;
  tabState = { ...tabState, activeId: tab.id };
  persistTabs();
  syncViewPanels();
  $.searchInput.focus();
}

function ensureActiveSearchTab() {
  let tab = activeTab();
  if (tab?.view === VIEW.SEARCH) return tab;
  tab = firstSearchTab();
  if (tab) {
    focusSearchTab(tab);
    return tab;
  }
  addSearchTab();
  return activeTab();
}

function showSearch({ replace = false } = {}) {
  const tab = ensureActiveSearchTab();
  if (!tab) return;
  syncViewPanels();
  if (!replace) updateBrowserUrlFromActiveTab(false);
}

function showGuide({ replace = false } = {}) {
  openSingletonViewTab(VIEW.GUIDE, createGuideTab);
  if (!replace) updateBrowserUrlFromActiveTab(false);
}

function showRelation({ replace = false } = {}) {
  openSingletonViewTab(VIEW.RELATION, createRelationTab);
  if (!replace) updateBrowserUrlFromActiveTab(false);
}

function goHome() {
  const tab = activeTab();
  if (!tab) return;
  if (tab.view !== VIEW.SEARCH) {
    let searchTab = firstSearchTab();
    if (!searchTab) {
      addSearchTab();
      searchTab = activeTab();
    }
    if (searchTab) focusSearchTab(searchTab);
  }
  const active = activeTab();
  if (!active || active.view !== VIEW.SEARCH) return;
  active.q = "";
  active.results = [];
  active.offset = 0;
  active.total = null;
  $.searchInput.value = "";
  $.results.innerHTML = "";
  $.results.className = "results";
  $.stats.textContent = "";
  toggleLoadMoreButton(false);
  updateShuffleButton();
  persistTabs();
  syncViewPanels();
  updateBrowserUrlFromActiveTab(true);
  $.searchInput.focus();
}
