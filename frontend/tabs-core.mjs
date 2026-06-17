import {
  $,
  VIEW,
  shell,
  SESSION_KEY,
  serializeSession,
  deserializeSession,
  createSearchTab,
  applyUrlToTabs,
  buildUrlSearchParams,
  tabLabel,
  searchParamsWithoutBoot,
} from "./app-context.mjs";
import { relationPayloadFromForm } from "./relation-form.mjs";

function activeTab() {
  return shell.tabState.tabs.find((t) => t.id === shell.tabState.activeId) || shell.tabState.tabs[0];
}

function firstSearchTab() {
  return shell.tabState.tabs.find((t) => t.view === VIEW.SEARCH) || null;
}

function persistTabs() {
  try {
    sessionStorage.setItem(SESSION_KEY, serializeSession(shell.tabState));
  } catch {
    /* ignore quota */
  }
}

function loadTabsFromSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return false;
    shell.tabState = deserializeSession(raw);
    return true;
  } catch {
    return false;
  }
}

function ensureDefaultTabs(parsed) {
  if (loadTabsFromSession()) return;
  shell.tabState = applyUrlToTabs(null, parsed);
  if (!shell.tabState.tabs.length) {
    shell.tabState = { activeId: 1, nextTabId: 2, tabs: [createSearchTab({ id: 1 })] };
  }
}

function saveActiveTabFromUi() {
  const tab = activeTab();
  if (!tab) return;
  if (tab.view === VIEW.SEARCH) {
    tab.q = $.searchInput.value;
  } else if (tab.view === VIEW.RELATION) {
    tab.relation = relationPayloadFromForm();
  }
}

function updateBrowserUrlFromActiveTab(replace = false) {
  const tab = activeTab();
  if (!tab) return;
  const params = buildUrlSearchParams(tab, shell.currentMode);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const url = `${window.location.pathname}${suffix}`;
  const state = {
    tabId: tab.id,
    view: tab.view,
    query: tab.view === VIEW.SEARCH ? tab.q || "" : "",
    mode: shell.currentMode,
  };
  if (replace) window.history.replaceState(state, "", url);
  else window.history.pushState(state, "", url);
}

function applyActiveNeighborDividerHides() {
  $.tabstrip.querySelectorAll(".chrome-tab").forEach((t) => {
    t.classList.remove("hide-left-divider-active", "hide-right-divider-active");
  });
  const active = $.tabstrip.querySelector(".chrome-tab[active]");
  if (!active) return;
  const prev = active.previousElementSibling;
  const next = active.nextElementSibling;
  if (prev && prev.classList.contains("chrome-tab") && !prev.classList.contains("chrome-tab-add")) {
    prev.classList.add("hide-right-divider-active");
  }
  if (next && next.classList.contains("chrome-tab") && !next.classList.contains("chrome-tab-add")) {
    next.classList.add("hide-left-divider-active");
  }
}

function markActiveTabInStrip(id) {
  $.tabstrip.querySelectorAll(".chrome-tab:not(.chrome-tab-add)").forEach((el) => {
    const tid = Number(el.dataset.tabId);
    const isActive = tid === id;
    if (isActive) el.setAttribute("active", "");
    else el.removeAttribute("active");
    const handle = el.querySelector("[data-tab]");
    if (handle) {
      handle.setAttribute("aria-selected", String(isActive));
      handle.setAttribute("tabindex", isActive ? "0" : "-1");
    }
  });
  applyActiveNeighborDividerHides();
}

function updateActiveTabTitle() {
  const tab = activeTab();
  if (!tab) return;
  const label = tabLabel(tab);
  const row = $.tabstrip.querySelector(`.chrome-tab[data-tab-id="${tab.id}"]`);
  if (!row) return;
  const titleEl = row.querySelector(".chrome-tab-title");
  if (titleEl) titleEl.textContent = label;
  const handle = row.querySelector(`[data-tab="${tab.id}"]`);
  if (handle) {
    handle.setAttribute("aria-label", label);
    handle.setAttribute("aria-selected", String(tab.id === shell.tabState.activeId));
  }
}

function animateNewTabEntry(tabId) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const el = $.tabstrip.querySelector(`.chrome-tab[data-tab-id="${tabId}"]`);
  if (!el) return;
  const finalMatch = el.style.transform.match(/translate3d\(([-\d.]+)px,\s*0,\s*0\)/);
  if (!finalMatch) return;
  const baseTransform = `translate3d(${finalMatch[1]}px, 0, 0)`;
  el.classList.add("chrome-tab-is-entering");
  el.style.transform = `${baseTransform} scaleX(0)`;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      let finished = false;
      const cleanup = () => {
        if (finished) return;
        finished = true;
        el.classList.remove("chrome-tab-is-entering");
        el.style.transform = baseTransform;
      };
      el.addEventListener(
        "transitionend",
        (e) => {
          if (e.propertyName !== "transform") return;
          cleanup();
        },
        { once: true }
      );
      el.style.transform = `${baseTransform} scaleX(1)`;
      setTimeout(cleanup, 260);
    });
  });
}

function updateTabstripLastMarkers() {
  const normal = [...$.tabstrip.querySelectorAll(".chrome-tab:not(.chrome-tab-add)")];
  normal.forEach((el) => el.classList.remove("chrome-tab-is-last"));
  if (normal.length) normal[normal.length - 1].classList.add("chrome-tab-is-last");
}

function scrollActiveTabIntoView() {
  const active = $.tabstrip.querySelector(".chrome-tab[active]");
  if (active) active.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
}

function stripLauncherBootFromUrl() {
  const next = searchParamsWithoutBoot(new URLSearchParams(window.location.search));
  if (!next) return;
  const suffix = next.toString() ? `?${next.toString()}` : "";
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${suffix}${window.location.hash}`);
}

export {
  activeTab,
  animateNewTabEntry,
  applyActiveNeighborDividerHides,
  ensureDefaultTabs,
  firstSearchTab,
  markActiveTabInStrip,
  persistTabs,
  saveActiveTabFromUi,
  scrollActiveTabIntoView,
  stripLauncherBootFromUrl,
  updateActiveTabTitle,
  updateBrowserUrlFromActiveTab,
  updateTabstripLastMarkers,
};
