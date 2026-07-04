/** 共享狀態、DOM 引用、常數（frontend 模組根）。 */
import {
  SESSION_KEY,
  VIEW,
  tabLabel,
  findTabByView,
  openSingletonView,
  createSearchTab,
  createGuideTab,
  createRelationTab,
  createCorrectionsTab,
  createAboutTab,
  isCorrectionsSearchCommand,
  buildUrlSearchParams,
  parseUrlSearchParams,
  searchParamsWithoutBoot,
  LAUNCHER_BOOT_PARAM,
  serializeSession,
  deserializeSession,
  closeTab as closeTabInState,
  reorderTabsByIds,
  applyUrlToTabs,
} from "./query-tabs-state.mjs";

export {
  SESSION_KEY,
  VIEW,
  tabLabel,
  findTabByView,
  openSingletonView,
  createSearchTab,
  createGuideTab,
  createRelationTab,
  createCorrectionsTab,
  createAboutTab,
  isCorrectionsSearchCommand,
  buildUrlSearchParams,
  parseUrlSearchParams,
  searchParamsWithoutBoot,
  LAUNCHER_BOOT_PARAM,
  serializeSession,
  deserializeSession,
  closeTabInState,
  reorderTabsByIds,
  applyUrlToTabs,
};

export const APP_TITLE_BASE = "Canto-0243 ONE·搵·韻";
export const APP_TITLE_BASE_EN = "Canto-0243 ONE-RUN-RHYME";
export const APP_TITLE_PORTABLE_SUFFIX = " (移動版)";

export const LANG_KEY = 'canto-lang';
export const THEME_KEY = 'canto-theme';

const MESSAGES = {
  zh: {
    'hero.title': 'ONE·搵·韻',
    'hero.tagline': '格律／協音／押韻／近反義，一步搵到。',
    'search.label': '搜尋內容',
    'search.button': '搜尋',
    'search.placeholder.default': '輸入 香??、23+就=、~=開心、!!、~~…',
    'mode.readout.prefix': '目前模式：',
    'shuffle.aria': '隨機打亂結果',
    'brand.aria': '返回搜尋首頁',
    'menu.0243.group': '0243搜尋模式',
    'menu.tools': '工具',
    'menu.guide': '搜尋教學',
    'menu.guide.help': '完整語法與例子',
    'menu.about': '關於',
    'menu.about.help': '授權、致謝與回報',
    'about.title': '關於 Canto-0243',
    'about.lede': 'ONE·搵·韻 — 離線粵語填詞查找工作台。',
    'about.back': '返回搜尋',
    'gate.preparing': '執緊啲字…',
    'empty.notfound': '搵唔到',
    'lang.toggle': '中 / EN',
    'theme.toggle': '切換主題',
  },
  en: {
    'hero.title': 'ONE-RUN-RHYME',
    'hero.tagline': 'Meter / sound match / rhyme / near-antonyms — find in one step.',
    'search.label': 'Search',
    'search.button': 'Search',
    'search.placeholder.default': 'Try 香??, 23+就=, ~=happy, !!, ~~…',
    'mode.readout.prefix': 'Current mode: ',
    'shuffle.aria': 'Shuffle results',
    'brand.aria': 'Back to search home',
    'menu.0243.group': '0243 Search Modes',
    'menu.tools': 'Tools',
    'menu.guide': 'Search Guide',
    'menu.guide.help': 'Full syntax & examples',
    'menu.about': 'About',
    'menu.about.help': 'License, credits & feedback',
    'about.title': 'About Canto-0243',
    'about.lede': 'ONE-RUN-RHYME — Offline Cantonese lyric rhyme workbench.',
    'about.back': 'Back to search',
    'gate.preparing': 'Loading…',
    'empty.notfound': 'No matches',
    'lang.toggle': 'EN / 中',
    'theme.toggle': 'Toggle theme',
  },
};

export function getLang() {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === 'zh' || saved === 'en') return saved;
  return (navigator.language || '').startsWith('zh') ? 'zh' : 'en';
}

export function setLang(lang) {
  localStorage.setItem(LANG_KEY, lang);
  document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : 'en';
}

export function t(key, lang = getLang()) {
  return MESSAGES[lang]?.[key] ?? MESSAGES.zh[key] ?? key;
}

export function getTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function setTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.dataset.theme = theme;
  // update meta theme-color
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = theme === 'dark' ? '#1C1917' : '#EBDFD0';
}

export const MODE_META = {
  m1: {
    title: "0243模式",
    note: "鬆",
    readout: "0243模式（鬆）",
    statsLabel: "0243模式 · 鬆",
    placeholder: "搵嘢：0243／漢字／粵拼",
  },
  m2: {
    title: "02493模式",
    note: "緊",
    readout: "02493模式（緊）",
    statsLabel: "02493模式 · 緊",
    placeholder: "搵嘢：02493／漢字／粵拼",
  },
  syn: {
    title: "近反義",
    note: "查",
    readout: "近反義模式（查）",
    statsLabel: "近反義 · 查",
    placeholder: "打字搵同義／反義",
  },
};

export const PAGE_SIZE = 160;
export const WARMUP_DONE_HOLD_MS = 2000;
export const WARMUP_DONE_FADE_MS = 420;
export const SEARCH_RING_BLUR_MS = 320;
export const LANDING_VARIANT = document.documentElement.dataset.landing || "a";
export const LANDING_SESSION_KEY = "canto0243:landing-done";
export const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
export const LANDING_REVEAL_MS = 420;
export const LANDING_HANDOFF_MS = 640;
export const GATE_BRAND_INTRO_MS = 700;
export const GATE_NEAR_DONE_PCT = 85;
export const GATE_INK_CLIP_MAX = 200;

// ponytail: const shell — importers cannot assign to export let live bindings in browsers
export const shell = {
  currentMode: "m1",
  last0243Mode: "m1",
  isSearching: false,
  searchAbort: null,
  appSearchReady: false,
  tabState: { activeId: 1, nextTabId: 2, tabs: [] },
  chromeLayout: null,
  pendingNewTabAnimation: null,
  lastHistSeq: 0,
};
export function setAppSearchReady(ready) {
  shell.appSearchReady = ready;
}

export const $ = {
  homeBtn: document.getElementById("homeBtn"),
  portableExitBtn: document.getElementById("portableExitBtn"),
  guideMenuBtn: document.getElementById("guideMenuBtn"),
  relationMenuBtn: document.getElementById("relationMenuBtn"),
  aboutMenuBtn: document.getElementById("aboutMenuBtn"),
  modeMenuButton: document.getElementById("modeMenuButton"),
  modeMenu: document.getElementById("modeMenu"),
  currentModeLabel: document.getElementById("currentModeLabel"),
  modeReadout: document.getElementById("modeReadout"),
  searchView: document.getElementById("searchView"),
  guideView: document.getElementById("guideView"),
  aboutView: document.getElementById("aboutView"),
  relationView: document.getElementById("relationView"),
  chromeTabs: document.getElementById("queryChromeTabs"),
  tabstrip: document.getElementById("queryTabstrip"),
  searchForm: document.getElementById("searchForm"),
  searchInputWrap: document.getElementById("searchInputWrap"),
  searchInput: document.getElementById("searchInput"),
  queryExplain: document.getElementById("queryExplain"),
  queryExplainSummary: document.getElementById("queryExplainSummary"),
  queryExplainWarning: document.getElementById("queryExplainWarning"),
  searchBtn: document.getElementById("searchBtn"),
  shuffleBtn: document.getElementById("shuffleBtn"),
  results: document.getElementById("results"),
  stats: document.getElementById("stats"),
  relationForm: document.getElementById("relationForm"),
  seedChar: document.getElementById("seedChar"),
  oppositeChar: document.getElementById("oppositeChar"),
  relationSubmitBtn: document.getElementById("relationSubmitBtn"),
  relationRevokeBtn: document.getElementById("relationRevokeBtn"),
  relationOkStatus: document.getElementById("relationOkStatus"),
  relationErrStatus: document.getElementById("relationErrStatus"),
  correctionsView: document.getElementById("correctionsView"),
  correctionsLookupForm: document.getElementById("correctionsLookupForm"),
  correctionChar: document.getElementById("correctionChar"),
  correctionLookupBtn: document.getElementById("correctionLookupBtn"),
  correctionRowsPanel: document.getElementById("correctionRowsPanel"),
  correctionRowList: document.getElementById("correctionRowList"),
  correctionsSubmitForm: document.getElementById("correctionsSubmitForm"),
  correctionNewJyutping: document.getElementById("correctionNewJyutping"),
  correctionNote: document.getElementById("correctionNote"),
  correctionCodePreview: document.getElementById("correctionCodePreview"),
  correctionJyutpingBtn: document.getElementById("correctionJyutpingBtn"),
  correctionRecalcCodeBtn: document.getElementById("correctionRecalcCodeBtn"),
  correctionOkStatus: document.getElementById("correctionOkStatus"),
  correctionErrStatus: document.getElementById("correctionErrStatus"),
  correctionSessionPanel: document.getElementById("correctionSessionPanel"),
  correctionSessionList: document.getElementById("correctionSessionList"),
  preloadOverlay: document.getElementById("preloadOverlay"),
  preloadLabel: document.getElementById("preloadLabel"),
  gateInkClipRect: document.getElementById("gateInkClipRect"),
  gateInkClipRectMini: document.getElementById("gateInkClipRectMini"),
  appShell: document.getElementById("appShell"),
  warmupBadge: document.getElementById("warmupBadge"),
  warmupBadgeLabel: document.getElementById("warmupBadgeLabel"),
  warmupBadgePct: document.getElementById("warmupBadgePct"),
  warmupInkClipRect: document.getElementById("warmupInkClipRect"),
};

export const searchCache = new Map();

export function readPortableBootstrapFlag() {
  return document.querySelector('meta[name="canto-portable"]')?.content === "1";
}

export function applyAppTitle(portable = false, lang = getLang()) {
  const base = lang === 'en' ? APP_TITLE_BASE_EN : APP_TITLE_BASE;
  const title = portable ? `${base}${APP_TITLE_PORTABLE_SUFFIX}` : base;
  document.title = title;
  if ($.portableExitBtn) {
    $.portableExitBtn.hidden = !portable;
  }
}
