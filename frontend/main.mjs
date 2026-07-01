import {
  MODE_META,
  SEARCH_RING_BLUR_MS,
  shell,
  applyAppTitle,
  parseUrlSearchParams,
  createGuideTab,
  createRelationTab,
  createCorrectionsTab,
  VIEW,
  $,
} from "./app-context.mjs";
import { waitForPreloadReady } from "./gate.mjs";
import { QueryChromeTabsLayout } from "./chrome-tabs-layout.mjs";
import {
  activeTab,
  persistTabs,
  ensureDefaultTabs,
  saveActiveTabFromUi,
  updateActiveTabTitle,
  stripLauncherBootFromUrl,
  updateBrowserUrlFromActiveTab,
} from "./tabs-core.mjs";
import { syncViewPanels } from "./view-sync.mjs";
import {
  addSearchTab,
  closeTab,
  openSingletonViewTab,
  ensureActiveSearchTab,
  showSearch,
  showGuide,
  showRelation,
  showAbout,
  goHome,
} from "./tabs-ui.mjs";
import {
  updateModeLabel,
  toggleMenu,
  switchMode,
  runExample,
  shuffleResults,
  searchDict,
  wireModeMenuKeyboard,
} from "./search-workbench.mjs";
import { refreshQueryExplain, scheduleQueryExplain } from "./query-explain.mjs";
import {
  ensureSearchTabHistory,
  isHistoryForward,
  stepSearchTabBack,
} from "./search-navigation.mjs";
import {
  relationPayloadFromForm,
  postRelation,
  showRelationOk,
  showRelationErr,
} from "./relation-form.mjs";

function showFileFallback() {
  document.body.innerHTML = "";
  const wrap = document.createElement("main");
  wrap.className = "file-fallback";

  const card = document.createElement("section");
  card.className = "file-card";
  card.setAttribute("aria-labelledby", "fileFallbackTitle");

  const title = document.createElement("h1");
  title.id = "fileFallbackTitle";
  title.textContent = "Canto-0243";

  const copy = document.createElement("p");
  copy.textContent = "你直接開啟了 index.html。此工具需要後端伺服器支援，請先啟動本地服務。";

  const note = document.createElement("div");
  note.className = "file-note";
  note.textContent = "請先執行 start.sh，再開啟應用程式。";

  const link = document.createElement("a");
  link.className = "primary-button";
  link.href = "http://127.0.0.1:8000/frontend/index.html";
  link.textContent = "開啟應用程式";

  card.append(title, copy, note, link);
  wrap.appendChild(card);
  document.body.appendChild(wrap);
}

if (location.protocol === "file:") {
  document.addEventListener("DOMContentLoaded", showFileFallback);
  throw new Error("Direct file open - showing instruction only");
}

function bindInputDualRing(wrap) {
  const input = wrap.querySelector("input");
  if (!input) return;
  input.addEventListener("focus", () => {
    wrap.classList.remove("is-blurring");
    wrap.classList.add("is-focused");
  });
  input.addEventListener("blur", () => {
    wrap.classList.remove("is-focused");
    wrap.classList.add("is-blurring");
    window.setTimeout(() => wrap.classList.remove("is-blurring"), SEARCH_RING_BLUR_MS);
  });
}

function bindSearchDualRing() {
  if (!$.searchInputWrap || !$.searchInput) return;
  $.searchInput.addEventListener("focus", () => {
    $.searchInputWrap.classList.remove("is-blurring");
    $.searchInputWrap.classList.add("is-focused");
  });
  $.searchInput.addEventListener("blur", () => {
    $.searchInputWrap.classList.remove("is-focused");
    $.searchInputWrap.classList.add("is-blurring");
    window.setTimeout(() => $.searchInputWrap.classList.remove("is-blurring"), SEARCH_RING_BLUR_MS);
  });
}
bindSearchDualRing();
document.querySelectorAll("[data-input-wrap]").forEach(bindInputDualRing);

$.searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  searchDict();
});

$.shuffleBtn.addEventListener("click", shuffleResults);

$.searchInput.addEventListener("input", () => {
  const tab = activeTab();
  if (tab?.view === VIEW.SEARCH) {
    tab.q = $.searchInput.value;
    persistTabs();
    updateActiveTabTitle();
    scheduleQueryExplain($.searchInput.value);
  }
});

$.homeBtn.addEventListener("click", goHome);
$.modeMenuButton.addEventListener("click", () => toggleMenu());
$.guideTopBtn.addEventListener("click", () => showGuide());
$.guideMenuBtn.addEventListener("click", () => showGuide());
$.relationTopBtn.addEventListener("click", () => showRelation());
$.relationMenuBtn.addEventListener("click", () => showRelation());
$.aboutTopBtn.addEventListener("click", () => showAbout());
document.getElementById("aboutBackToSearchBtn")?.addEventListener("click", () => {
  showSearch();
  $.searchInput.focus();
});
$.backToSearchBtn.addEventListener("click", () => {
  showSearch();
  $.searchInput.focus();
});

$.relationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  $.relationOkStatus.hidden = true;
  $.relationErrStatus.hidden = true;
  $.relationSubmitBtn.disabled = true;
  $.relationRevokeBtn.disabled = true;
  saveActiveTabFromUi();
  try {
    const { response, body } = await postRelation("/relations/manual", relationPayloadFromForm());
    if (!response.ok) {
      showRelationErr(body.detail || "提交失敗，請稍後再試。");
      return;
    }
    showRelationOk(body.message || "已補上關係。");
  } catch {
    showRelationErr("無法連線後端。請確認伺服器已啟動。");
  } finally {
    $.relationSubmitBtn.disabled = false;
    $.relationRevokeBtn.disabled = false;
  }
});

$.relationRevokeBtn.addEventListener("click", async () => {
  $.relationOkStatus.hidden = true;
  $.relationErrStatus.hidden = true;
  $.relationSubmitBtn.disabled = true;
  $.relationRevokeBtn.disabled = true;
  saveActiveTabFromUi();
  try {
    const { response, body } = await postRelation("/relations/manual/revoke", relationPayloadFromForm());
    if (!response.ok) {
      showRelationErr(body.detail || "撤回失敗，請稍後再試。");
      return;
    }
    showRelationOk(body.message || "已撤回關係。");
  } catch {
    showRelationErr("無法連線後端。請確認伺服器已啟動。");
  } finally {
    $.relationSubmitBtn.disabled = false;
    $.relationRevokeBtn.disabled = false;
  }
});

document.querySelectorAll("[data-mode].mode-option").forEach((btn) => {
  btn.addEventListener("click", () => switchMode(btn.dataset.mode));
});

document.querySelectorAll("[data-query]").forEach((btn) => {
  btn.addEventListener("click", () => runExample(btn.dataset.query || "", btn.dataset.mode || shell.currentMode));
});

document.addEventListener("click", (event) => {
  if (!$.modeMenu.contains(event.target) && !$.modeMenuButton.contains(event.target)) {
    toggleMenu(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") toggleMenu(false, { returnFocus: true });
  if (!event.altKey || event.ctrlKey || event.metaKey) return;
  const key = event.key.toLowerCase();
  if (key === "n") {
    event.preventDefault();
    addSearchTab();
    return;
  }
  if (key === "w") {
    event.preventDefault();
    closeTab(shell.tabState.activeId);
  }
});

let suppressPopstateStep = false;

window.addEventListener("popstate", (event) => {
  const state = event.state || {};
  const tab = activeTab();
  const seq = state._histSeq;

  if (tab?.view !== VIEW.SEARCH) {
    if (typeof seq === "number") shell.lastHistSeq = seq;
    updateBrowserUrlFromActiveTab(true);
    return;
  }

  if (suppressPopstateStep) {
    suppressPopstateStep = false;
    if (typeof seq === "number") shell.lastHistSeq = seq;
    updateBrowserUrlFromActiveTab(true);
    return;
  }

  if (isHistoryForward(shell.lastHistSeq, state)) {
    suppressPopstateStep = true;
    history.back();
    return;
  }

  if (typeof seq === "number") shell.lastHistSeq = seq;

  const frame = stepSearchTabBack(tab);
  if (!frame) {
    suppressPopstateStep = true;
    history.forward();
    updateBrowserUrlFromActiveTab(true);
    return;
  }

  shell.currentMode = MODE_META[frame.mode] ? frame.mode : shell.currentMode;
  updateModeLabel();
  persistTabs();
  syncViewPanels();
  updateBrowserUrlFromActiveTab(true);
  if (frame.q) {
    searchDict(false, true);
  } else {
    tab.results = [];
    tab.offset = 0;
    tab.total = null;
    persistTabs();
    syncViewPanels();
  }
});

(async function init() {
  await waitForPreloadReady();
  stripLauncherBootFromUrl();

  fetch("/")
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => applyAppTitle(Boolean(data && data.portable)))
    .catch(() => {});

  $.modeMenu.hidden = true;
  const parsed = parseUrlSearchParams(new URLSearchParams(window.location.search));
  shell.currentMode = MODE_META[parsed.mode] ? parsed.mode : "m1";
  if (shell.currentMode === "m1" || shell.currentMode === "m2") {
    shell.last0243Mode = shell.currentMode;
  }
  updateModeLabel();
  wireModeMenuKeyboard();
  ensureDefaultTabs(parsed);
  shell.lastHistSeq = window.history.state?._histSeq ?? 0;

  const urlTab = shell.tabState.tabs.find((t) => {
    if (parsed.view === VIEW.GUIDE) return t.view === VIEW.GUIDE;
    if (parsed.view === VIEW.RELATION) return t.view === VIEW.RELATION;
    if (parsed.view === VIEW.CORRECTIONS) return t.view === VIEW.CORRECTIONS;
    if (parsed.view === VIEW.ABOUT) return t.view === VIEW.ABOUT;
    return t.view === VIEW.SEARCH;
  });
  if (urlTab) shell.tabState = { ...shell.tabState, activeId: urlTab.id };
  if (parsed.view === VIEW.SEARCH && parsed.q) {
    const searchTab = shell.tabState.tabs.find((t) => t.id === shell.tabState.activeId && t.view === VIEW.SEARCH)
      || shell.tabState.tabs.find((t) => t.view === VIEW.SEARCH);
    if (searchTab) {
      searchTab.q = parsed.q;
      shell.tabState = { ...shell.tabState, activeId: searchTab.id };
    }
  }

  shell.tabState.tabs.forEach((t) => {
    if (t.view === VIEW.SEARCH) ensureSearchTabHistory(t, shell.currentMode);
  });

  shell.chromeLayout = new QueryChromeTabsLayout($.chromeTabs);
  syncViewPanels();
  updateBrowserUrlFromActiveTab(true);
  persistTabs();

  const active = activeTab();
  if (active?.view === VIEW.SEARCH && active.q) {
    searchDict(false, true);
  }
})();
