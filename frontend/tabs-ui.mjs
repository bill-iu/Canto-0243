import { escapeHtmlAttr } from "./dom-escape.mjs";
import { TAB_GEOMETRY_SVG } from "./tab-geometry.mjs";
import {
  $,
  VIEW,
  shell,
  createSearchTab,
  createGuideTab,
  createRelationTab,
  createCorrectionsTab,
  findTabByView,
  openSingletonView,
  reorderTabsByIds,
  closeTabInState,
  tabLabel,
} from "./app-context.mjs";
import {
  activeTab, firstSearchTab, persistTabs, saveActiveTabFromUi,
  updateBrowserUrlFromActiveTab, markActiveTabInStrip, animateNewTabEntry,
  updateTabstripLastMarkers, scrollActiveTabIntoView, applyActiveNeighborDividerHides,
} from "./tabs-core.mjs";
import { syncViewPanels } from "./view-sync.mjs";
import {
  toggleLoadMoreButton, updateShuffleButton, toggleMenu,
} from "./search-workbench.mjs";

function renderTabstrip() {
  const tabsHtml = shell.tabState.tabs
    .map((t, idx) => {
      const isActive = t.id === shell.tabState.activeId;
      const isLast = idx === shell.tabState.tabs.length - 1;
      const closeBtn =
        shell.tabState.tabs.length > 1
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
            <div class="chrome-tab-drag-handle" role="tab" tabindex="${isActive ? "0" : "-1"}" aria-selected="${isActive}" aria-label="${escapeHtmlAttr(label)}" data-tab="${t.id}"></div>
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
  if (shell.chromeLayout) {
    shell.chromeLayout.layout();
    setupTabDrag();
  }
  if (shell.pendingNewTabAnimation) {
    const { tabId } = shell.pendingNewTabAnimation;
    shell.pendingNewTabAnimation = null;
    animateNewTabEntry(tabId);
  }
  requestAnimationFrame(scrollActiveTabIntoView);
}

function setupTabDrag() {
  if (!shell.chromeLayout || typeof Draggabilly === "undefined") return;
  shell.chromeLayout.setupDraggabilly({
    onPointerDown(id) {
      activateTabOnPress(id);
    },
    onReorderEnd(orderedIds) {
      const next = reorderTabsByIds(shell.tabState, orderedIds);
      if (next === shell.tabState) return;
      shell.tabState = next;
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
  wireTabstripKeyboard();
}

let tabstripKeyboardWired = false;

function wireTabstripKeyboard() {
  if (tabstripKeyboardWired || !$.tabstrip) return;
  tabstripKeyboardWired = true;
  $.tabstrip.addEventListener("keydown", (event) => {
    const tabs = [...$.tabstrip.querySelectorAll("[data-tab][role='tab']")];
    const current = document.activeElement;
    const idx = tabs.indexOf(current);
    if (idx < 0) return;

    let nextIdx = -1;
    if (event.key === "ArrowRight") nextIdx = (idx + 1) % tabs.length;
    else if (event.key === "ArrowLeft") nextIdx = (idx - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIdx = 0;
    else if (event.key === "End") nextIdx = tabs.length - 1;
    else if (
      (event.key === "Delete" || event.key === "Backspace")
      && shell.tabState.tabs.length > 1
      && !event.altKey
      && !event.ctrlKey
      && !event.metaKey
    ) {
      event.preventDefault();
      const id = Number(current.dataset.tab);
      const neighbor = tabs[idx + 1] || tabs[idx - 1];
      closeTab(id);
      neighbor?.focus({ preventScroll: true });
      return;
    } else {
      return;
    }

    event.preventDefault();
    const id = Number(tabs[nextIdx].dataset.tab);
    selectTab(id);
    tabs[nextIdx].focus({ preventScroll: true });
  });
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
  if (shell.tabState.activeId === id) return;
  saveActiveTabFromUi();
  shell.tabState = { ...shell.tabState, activeId: id };
  persistTabs();
  markActiveTabInStrip(id);
  syncViewPanels({ renderTabstrip: false });
  const tab = activeTab();
  if (tab?.view === VIEW.SEARCH) $.searchInput.focus();
  else if (tab?.view === VIEW.GUIDE) document.getElementById("guideTitle")?.focus({ preventScroll: true });
  else if (tab?.view === VIEW.RELATION) $.seedChar?.focus({ preventScroll: true });
  else if (tab?.view === VIEW.CORRECTIONS) $.correctionChar?.focus({ preventScroll: true });
}

function addSearchTab() {
  saveActiveTabFromUi();
  const tab = createSearchTab({ id: shell.tabState.nextTabId });
  shell.pendingNewTabAnimation = { tabId: tab.id };
  shell.tabState = {
    activeId: tab.id,
    nextTabId: shell.tabState.nextTabId + 1,
    tabs: [...shell.tabState.tabs, tab],
  };
  persistTabs();
  syncViewPanels();
  if (activeTab()?.view === VIEW.SEARCH) $.searchInput.focus();
}

function closeTab(id) {
  if (shell.tabState.tabs.length <= 1) return;
  saveActiveTabFromUi();
  shell.tabState = closeTabInState(shell.tabState, id);
  persistTabs();
  syncViewPanels();
}

function selectTab(id) {
  if (shell.tabState.activeId === id) return;
  saveActiveTabFromUi();
  shell.tabState = { ...shell.tabState, activeId: id };
  persistTabs();
  syncViewPanels();
  const tab = activeTab();
  if (tab?.view === VIEW.SEARCH) $.searchInput.focus();
  else if (tab?.view === VIEW.GUIDE) document.getElementById("guideTitle")?.focus({ preventScroll: true });
  else if (tab?.view === VIEW.RELATION) $.seedChar?.focus({ preventScroll: true });
  else if (tab?.view === VIEW.CORRECTIONS) $.correctionChar?.focus({ preventScroll: true });
}

function openSingletonViewTab(view, createTab) {
  saveActiveTabFromUi();
  shell.tabState = openSingletonView(shell.tabState, view, createTab);
  const singleton = findTabByView(shell.tabState.tabs, view);
  if (singleton) shell.tabState = { ...shell.tabState, activeId: singleton.id };
  persistTabs();
  syncViewPanels();
  toggleMenu(false);
  if (view === VIEW.GUIDE) {
    document.getElementById("guideTitle")?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (view === VIEW.RELATION) {
    $.seedChar?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (view === VIEW.CORRECTIONS) {
    $.correctionChar?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function focusSearchTab(tab) {
  if (!tab || tab.view !== VIEW.SEARCH) return;
  shell.tabState = { ...shell.tabState, activeId: tab.id };
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

function showCorrections({ replace = false } = {}) {
  openSingletonViewTab(VIEW.CORRECTIONS, createCorrectionsTab);
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

export {
  addSearchTab,
  closeTab,
  ensureActiveSearchTab,
  goHome,
  openSingletonViewTab,
  renderTabstrip,
  showGuide,
  showRelation,
  showCorrections,
  showSearch,
};
