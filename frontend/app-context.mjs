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
  buildUrlSearchParams,
  parseUrlSearchParams,
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
  buildUrlSearchParams,
  parseUrlSearchParams,
  serializeSession,
  deserializeSession,
  closeTabInState,
  reorderTabsByIds,
  applyUrlToTabs,
};

export const APP_TITLE_BASE = "Canto-0243 ONE·搵·韻";
export const APP_TITLE_PORTABLE_SUFFIX = " (移動版)";

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

export const TAB_GEOMETRY_SVG = `
  <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <svg width="52%" height="100%"><use xlink:href="#query-tab-geometry" width="214" height="36" class="chrome-tab-geometry"/></svg>
    <g transform="scale(-1, 1)"><svg width="52%" height="100%" x="-100%" y="0"><use xlink:href="#query-tab-geometry" width="214" height="36" class="chrome-tab-geometry"/></svg></g>
  </svg>`;

export let currentMode = "m1";
export let last0243Mode = "m1";
export let isSearching = false;
export let appSearchReady = false;
export let tabState = { activeId: 1, nextTabId: 2, tabs: [] };
export let chromeLayout = null;
export let pendingNewTabAnimation = null;
export let lastReadySnapshot = null;
export let warmupDoneShown = false;
export let warmupTailShown = false;
export let warmupPollTimer = null;
export let warmupDismissTimer = null;

export const $ = {
  homeBtn: document.getElementById("homeBtn"),
  guideTopBtn: document.getElementById("guideTopBtn"),
  relationTopBtn: document.getElementById("relationTopBtn"),
  guideMenuBtn: document.getElementById("guideMenuBtn"),
  relationMenuBtn: document.getElementById("relationMenuBtn"),
  backToSearchBtn: document.getElementById("backToSearchBtn"),
  modeMenuButton: document.getElementById("modeMenuButton"),
  modeMenu: document.getElementById("modeMenu"),
  currentModeLabel: document.getElementById("currentModeLabel"),
  modeReadout: document.getElementById("modeReadout"),
  searchView: document.getElementById("searchView"),
  guideView: document.getElementById("guideView"),
  relationView: document.getElementById("relationView"),
  chromeTabs: document.getElementById("queryChromeTabs"),
  tabstrip: document.getElementById("queryTabstrip"),
  searchForm: document.getElementById("searchForm"),
  searchInputWrap: document.getElementById("searchInputWrap"),
  searchInput: document.getElementById("searchInput"),
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

export function applyAppTitle(portable = false) {
  const title = portable ? `${APP_TITLE_BASE}${APP_TITLE_PORTABLE_SUFFIX}` : APP_TITLE_BASE;
  document.title = title;
}
