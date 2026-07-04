import {
  MODE_META,
  SEARCH_RING_BLUR_MS,
  shell,
  applyAppTitle,
  readPortableBootstrapFlag,
  parseUrlSearchParams,
  createGuideTab,
  createRelationTab,
  createCorrectionsTab,
  VIEW,
  $,
  getLang,
  setLang,
  t,
  getTheme,
  setTheme,
  LANG_KEY,
  THEME_KEY,
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
$.guideMenuBtn.addEventListener("click", () => showGuide());
$.relationMenuBtn.addEventListener("click", () => showRelation());
$.aboutMenuBtn.addEventListener("click", () => showAbout());
$.portableExitBtn?.addEventListener("click", () => exitPortable());
document.getElementById("aboutBackToSearchBtn")?.addEventListener("click", () => {
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

const PORTABLE_EXIT_CONFIRM = "將關閉本機服務，未儲存工作唔會遺失。確定退出 Canto-0243？";

async function exitPortable() {
  if (!window.confirm(PORTABLE_EXIT_CONFIRM)) return;
  try {
    const response = await fetch("/shutdown", { method: "POST" });
    if (!response.ok) throw new Error("shutdown failed");
    window.close();
    window.setTimeout(() => {
      if (document.visibilityState === "visible") {
        document.body.replaceChildren();
        const note = document.createElement("p");
        note.className = "portable-exit-note";
        note.textContent = "Canto-0243 已退出。你可以關閉此分頁。";
        document.body.appendChild(note);
      }
    }, 400);
  } catch {
    window.alert("無法關閉本機服務。請稍後再試，或使用工作管理員結束 pythonw.exe。");
  }
}

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

async function refreshPortableChrome() {
  try {
    const res = await fetch("/", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    applyAppTitle(Boolean(data?.portable));
  } catch {
    /* ponytail: meta tag from /frontend/index.html is the reload fallback */
  }
}

(async function init() {
  applyAppTitle(readPortableBootstrapFlag());
  void refreshPortableChrome();
  await waitForPreloadReady();
  stripLauncherBootFromUrl();
  await refreshPortableChrome();

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

  // Theme + Lang dual mode init (light/dark + 中/EN) — now inside dropdown menu
  function applyLangToChrome(lang) {
    // hero
    const h1 = document.getElementById('searchTitle');
    if (h1) h1.textContent = t('hero.title', lang);
    const tag = document.querySelector('.hero p:not(.eyebrow)');
    if (tag) tag.textContent = t('hero.tagline', lang);

    // search form
    const label = document.querySelector('.field-label[for="searchInput"]');
    if (label) label.textContent = t('search.label', lang);
    const input = document.getElementById('searchInput');
    if (input && !input.value) input.placeholder = t('search.placeholder.default', lang);
    const btn = document.getElementById('searchBtn');
    if (btn) btn.textContent = t('search.button', lang);

    // shuffle
    const shuffle = document.getElementById('shuffleBtn');
    if (shuffle) {
      shuffle.setAttribute('aria-label', t('shuffle.aria', lang));
      shuffle.setAttribute('title', t('shuffle.aria', lang));
    }

    // brand
    const brand = document.getElementById('homeBtn');
    if (brand) brand.setAttribute('aria-label', t('brand.aria', lang));

    // menu labels (update on fly for i18n)
    document.querySelectorAll('.menu-label').forEach(el => {
      const txt = el.textContent.trim();
      if (txt.includes('0243') || txt.includes('搜尋模式') || txt.includes('Search Modes')) {
        el.textContent = t('menu.0243.group', lang);
      } else if (txt === '工具' || txt === 'Tools') {
        el.textContent = t('menu.tools', lang);
      } else if (txt === '顯示' || txt === 'Display') {
        el.textContent = lang === 'zh' ? '顯示' : 'Display';
      }
    });

    // portable exit
    if ($.portableExitBtn && !$.portableExitBtn.hidden) {
      $.portableExitBtn.textContent = lang === 'en' ? 'Exit Canto-0243' : '退出 Canto-0243';
    }

    applyAppTitle(readPortableBootstrapFlag(), lang);

    // update theme/lang menu checks and labels
    updateThemeLangMenuUI(lang);
  }

  function updateThemeLangMenuUI(lang = getLang()) {
    const currentTheme = document.documentElement.dataset.theme || 'light';
    const currentLang = lang;

    // theme switch icon
    const themeBtn = document.getElementById('theme-switch');
    if (themeBtn) {
      const icon = themeBtn.querySelector('.theme-icon');
      if (icon) icon.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
      themeBtn.setAttribute('aria-label', lang === 'zh' ? '切換主題' : 'Toggle theme');
      themeBtn.setAttribute('title', lang === 'zh' ? '切換主題' : 'Toggle theme');
    }

    // lang switch text
    const langBtn = document.getElementById('lang-switch');
    const langText = document.getElementById('lang-switch-text');
    if (langBtn && langText) {
      langText.textContent = lang === 'zh' ? '中 / EN' : 'EN / 中';
      langBtn.setAttribute('aria-label', lang === 'zh' ? '切換語言' : 'Toggle language');
      langBtn.setAttribute('title', lang === 'zh' ? '切換語言' : 'Toggle language');
    }

    // update display label
    const displayLabel = document.getElementById('displayMenuLabel');
    if (displayLabel) {
      displayLabel.textContent = lang === 'zh' ? '顯示' : 'Display';
    }
    // update group aria-label
    const displayGroup = document.querySelector('#modeMenu .menu-group[aria-label="顯示"], #modeMenu .menu-group[aria-label="Display"]');
    if (displayGroup) displayGroup.setAttribute('aria-label', lang === 'zh' ? '顯示' : 'Display');
  }

  function applyTheme(theme) {
    setTheme(theme);
    updateThemeLangMenuUI();
  }

  function initThemeLang() {
    const lang = getLang();
    setLang(lang);

    const theme = getTheme();
    setTheme(theme);  // ensure html attr

    applyLangToChrome(lang);

    // wire the compact switches in dropdown (icons + single toggle, side by side)
    const themeBtn = document.getElementById('theme-switch');
    if (themeBtn) {
      themeBtn.onclick = () => {
        const current = document.documentElement.dataset.theme || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        const menu = document.getElementById('modeMenu');
        if (menu) menu.classList.remove('is-open');
      };
    }

    const langBtn = document.getElementById('lang-switch');
    if (langBtn) {
      langBtn.onclick = () => {
        const next = getLang() === 'zh' ? 'en' : 'zh';
        setLang(next);
        applyLangToChrome(next);
        if (typeof updateModeLabel === 'function') updateModeLabel(next);
        const menu = document.getElementById('modeMenu');
        if (menu) menu.classList.remove('is-open');
      };
    }

    // initial menu UI
    updateThemeLangMenuUI(lang);

    // respect system changes for theme if no explicit
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem(THEME_KEY)) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  }

  initThemeLang();
})();
