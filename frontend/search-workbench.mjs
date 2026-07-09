import { isRelationSyntaxQuery, modeRedirectHint } from "./relation-syntax.mjs";
import {
  isPingZeSerialQuery,
  pingZeEffectiveMode,
  pingZeModeRedirectHint,
} from "./ping-ze-syntax.mjs";
import { escapeHtml, escapeHtmlAttr } from "./dom-escape.mjs";
import {
  $,
  MODE_META,
  searchPageSizeForMode,
  searchLimitForOffset,
  SEARCH_FIRST_PAGE_SIZE,
  shell,
  searchCache,
  VIEW,
  getLang,
  getModeMeta,
  syncPortableModeMenu,
  t,
} from "./app-context.mjs";
import { wordCacheProgress, setGateInkProgress } from "./gate.mjs";
import {
  activeTab, persistTabs, updateBrowserUrlFromActiveTab,
} from "./tabs-core.mjs";
import {
  ensureActiveSearchTab, showSearch, showCorrections,
} from "./tabs-ui.mjs";
import { syncViewPanels } from "./view-sync.mjs";
import { isCorrectionsSearchCommand } from "./query-tabs-state.mjs";
import {
  buildResultSearchHref,
  commitSearchHistoryFrame,
  withResultClickQuery,
} from "./search-navigation.mjs";
import {
  mergeResultsByLiteral,
  mergePickLookupResults,
  pickReadingsToQueryRows,
  anchorOnlyQueryRow,
  resolveListClickAction,
  isListableWordRow,
  buildEntryDetailModelFromPick,
} from "./entry-detail-core.mjs";
import {
  createEntryDetailPanel,
  fetchEntryDetail,
  renderMergedResultList,
  appendPickLookupTail,
  createMergedResultButton,
} from "./entry-detail-portable.mjs";
import {
  RESULT_RENDER_BATCH,
  wireInfiniteScroll,
  effectiveRenderedCount,
  canExpandRenderedCount,
  expandRenderedCount,
  resetRenderedCount,
} from "./infinite-results.mjs";

function emptySearchResultsHtml(input, hint, _mode) {
  const q = escapeHtml(input);
  if (hint) {
    return `<p class="info"><strong>搵唔到</strong><br>${escapeHtml(hint)}</p>`;
  }
  return `<p class="info"><strong>搵唔到「${q}」。</strong></p>`;
}

function shouldShowLoadMore(tab) {
  const results = tab.results || [];
  const total = tab.total;
  // 首屏 400 已滿亦視為可能仲有；續頁用上限 800
  const threshold =
    shell.currentMode === "syn"
      ? searchPageSizeForMode(shell.currentMode)
      : SEARCH_FIRST_PAGE_SIZE;
  return (total != null && results.length < total) || results.length >= threshold;
}

function countSearchResultItems(data) {
  if (!data?.length) return 0;
  if (shell.currentMode === "syn") {
    return data.filter(
      (r) => r.relation === "syn" || r.relation === "ant" || r.relation === "semantic_related",
    ).length;
  }
  const initialHits = data.filter((r) => r.anchor_dimension === "initial");
  const finalHits = data.filter((r) => r.anchor_dimension === "final");
  if (initialHits.length || finalHits.length) {
    const initialMerged = mergeResultsByLiteral(
      initialHits.map((row) => ({ ...row, word: row.char || row.display_text })),
    );
    const finalMerged = mergeResultsByLiteral(
      finalHits.map((row) => ({ ...row, word: row.char || row.display_text })),
    );
    return initialMerged.length + finalMerged.length;
  }
  const rows = data.filter((row) => isListableWordRow({ ...row, word: row.char }));
  return mergeResultsByLiteral(
    rows.map((row) => ({ ...row, word: row.display_text || row.char })),
  ).length;
}

function takeSynBudget(syns, ants, related, budget) {
  const synsShown = syns.slice(0, budget);
  let left = budget - synsShown.length;
  const antsShown = ants.slice(0, Math.max(0, left));
  left -= antsShown.length;
  const relatedShown = related.slice(0, Math.max(0, left));
  return { synsShown, antsShown, relatedShown };
}

let scrollGate = false;

function isStandardWordListLayout(data) {
  if (shell.currentMode === "syn") return false;
  return !data.some((r) => r.anchor_dimension === "initial" || r.anchor_dimension === "final");
}

function mergedWordGroups(data) {
  const rows = data.filter((row) => isListableWordRow({ ...row, word: row.char }));
  return mergeResultsByLiteral(
    rows.map((row) => ({ ...row, word: row.display_text || row.char })),
  );
}

function updateWordListStats(mergedLen, total, loadedLen) {
  const statsLabel = getModeMeta(shell.currentMode, getLang()).statsLabel;
  if (total != null && total > loadedLen) {
    $.stats.textContent = `已載入 ${loadedLen} / ${total} 個結果（${statsLabel}）`;
  } else if (total != null) {
    $.stats.textContent = `${total} 個結果（${statsLabel}）`;
  } else {
    $.stats.textContent = `${mergedLen} 個結果（${statsLabel}）`;
  }
}

function appendWordListSlice(ul, merged, from, to, lang) {
  merged.slice(from, to).forEach((group) =>
    ul.appendChild(
      createMergedResultButton(group, {
        lang,
        activeLiteral: shell.entryDetail.activeLiteral,
        onPick: handleEntryPick,
      }),
    ),
  );
}

function updateScrollSentinel(tab) {
  const sentinel = $.resultsScrollSentinel;
  if (!sentinel) return;
  const itemCount = countSearchResultItems(tab?.results || []);
  const canExpand = tab && canExpandRenderedCount(tab, itemCount);
  const canFetch = tab && shouldShowLoadMore(tab);
  sentinel.hidden = itemCount === 0 || (!canExpand && !canFetch);
}

function handleInfiniteScrollNeed() {
  if (scrollGate || shell.isSearching) return;
  const tab = activeTab();
  if (!tab || tab.view !== VIEW.SEARCH) return;
  const data = tab.results || [];
  const itemCount = countSearchResultItems(data);
  if (canExpandRenderedCount(tab, itemCount)) {
    scrollGate = true;
    const prevRendered = effectiveRenderedCount(tab, itemCount);
    expandRenderedCount(tab, itemCount);
    persistTabs();
    renderSearchResults(data, tab.total, { expandFrom: prevRendered });
    scrollGate = false;
    remountInfiniteScroll();
    return;
  }
  if (shouldShowLoadMore(tab)) searchDict(true);
}

const SEARCH_LOADING_LABEL_DELAY_MS = 150;
let searchLoadingLabelTimer = null;

function clearSearchLoadingLabelTimer() {
  if (searchLoadingLabelTimer) {
    clearTimeout(searchLoadingLabelTimer);
    searchLoadingLabelTimer = null;
  }
}

function setButtonLoading(loading, { staleResults = false } = {}) {
  shell.isSearching = loading;
  $.searchBtn.disabled = loading || !shell.appSearchReady;
  clearSearchLoadingLabelTimer();
  if (!loading) {
    $.searchBtn.textContent = "搜尋";
    return;
  }
  if (staleResults) return;
  searchLoadingLabelTimer = setTimeout(() => {
    if (shell.isSearching) $.searchBtn.textContent = "搜尋中…";
  }, SEARCH_LOADING_LABEL_DELAY_MS);
}

function updateModeLabel(lang = getLang()) {
  const meta = getModeMeta(shell.currentMode, lang);
  $.currentModeLabel.innerHTML =
    `<span class="mode-trigger-primary">${meta.title}</span><span class="mode-trigger-note">${meta.note}</span>`;
  $.modeReadout.textContent = `${t('mode.readout.prefix', lang)}${meta.readout}`;
  $.searchInput.placeholder = meta.placeholder;
  syncPortableModeMenu(lang);
  document.querySelectorAll("[data-mode]").forEach((btn) => {
    if (!btn.classList.contains("mode-option")) return;
    btn.setAttribute("aria-checked", btn.dataset.mode === shell.currentMode ? "true" : "false");
  });
}

let modeMenuKeyboardWired = false;

function modeMenuItems() {
  return [...$.modeMenu.querySelectorAll('[role="menuitem"], [role="menuitemradio"]')];
}

function syncModeMenuTabindex(focusIndex) {
  const items = modeMenuItems();
  items.forEach((el, i) => {
    el.setAttribute("tabindex", i === focusIndex ? "0" : "-1");
  });
  items[focusIndex]?.focus({ preventScroll: true });
}

function wireModeMenuKeyboard() {
  if (modeMenuKeyboardWired || !$.modeMenu) return;
  modeMenuKeyboardWired = true;
  modeMenuItems().forEach((el) => el.setAttribute("tabindex", "-1"));
  $.modeMenu.addEventListener("keydown", (event) => {
    const items = modeMenuItems();
    const idx = items.indexOf(document.activeElement);
    if (idx < 0) return;

    let nextIdx = -1;
    if (event.key === "ArrowDown") nextIdx = (idx + 1) % items.length;
    else if (event.key === "ArrowUp") nextIdx = (idx - 1 + items.length) % items.length;
    else if (event.key === "Home") nextIdx = 0;
    else if (event.key === "End") nextIdx = items.length - 1;
    else if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      document.activeElement?.click();
      return;
    } else {
      return;
    }

    event.preventDefault();
    syncModeMenuTabindex(nextIdx);
  });
}

function toggleMenu(open, { returnFocus = false } = {}) {
  const nextOpen = typeof open === "boolean"
    ? open
    : $.modeMenuButton.getAttribute("aria-expanded") !== "true";
  $.modeMenuButton.setAttribute("aria-expanded", String(nextOpen));
  $.modeMenu.classList.toggle("is-open", nextOpen);
  $.modeMenu.hidden = !nextOpen;
  if (nextOpen) {
    wireModeMenuKeyboard();
    const items = modeMenuItems();
    const checked = $.modeMenu.querySelector('[role="menuitemradio"][aria-checked="true"]');
    const focusIdx = checked ? Math.max(0, items.indexOf(checked)) : 0;
    syncModeMenuTabindex(focusIdx);
  } else {
    modeMenuItems().forEach((el) => el.setAttribute("tabindex", "-1"));
    if (returnFocus) $.modeMenuButton.focus();
  }
}

function switchMode(mode, { runSearch = true, replace = true } = {}) {
  if (!MODE_META[mode]) return;
  if (
    mode === "syn" &&
    (shell.currentMode === "m1" || shell.currentMode === "m2" || shell.currentMode === "m3")
  ) {
    shell.last0243Mode = shell.currentMode;
  }
  shell.currentMode = mode;
  updateModeLabel();
  toggleMenu(false);

  const tab = activeTab();
  const input = tab?.view === VIEW.SEARCH ? $.searchInput.value.trim() : "";
  if (input && tab?.view === VIEW.SEARCH && runSearch) {
    updateBrowserUrlFromActiveTab(false);
    searchDict(false, true);
  } else {
    updateBrowserUrlFromActiveTab(replace);
  }
}

function runExample(query, mode = shell.currentMode) {
  switchMode(mode, { runSearch: false, replace: true });
  const tab = ensureActiveSearchTab();
  if (!tab) return;
  tab.q = query;
  $.searchInput.value = query;
  persistTabs();
  syncViewPanels();
  searchDict(false);
}

let entryDetailUi = null;
let entryDetailInsetBound = false;

function syncEntryDetailInset() {
  const header = document.querySelector(".app-header");
  document.documentElement.style.setProperty(
    "--entry-detail-inset-top",
    header ? `${header.getBoundingClientRect().bottom}px` : "0px",
  );
}

function bindEntryDetailInset() {
  if (entryDetailInsetBound) return;
  entryDetailInsetBound = true;
  document.documentElement.classList.add("has-entry-detail-open");
  window.addEventListener("resize", syncEntryDetailInset);
  const header = document.querySelector(".app-header");
  if (header && typeof ResizeObserver !== "undefined") {
    entryDetailInsetRo = new ResizeObserver(syncEntryDetailInset);
    entryDetailInsetRo.observe(header);
  }
}

let entryDetailInsetRo = null;

function unbindEntryDetailInset() {
  if (!entryDetailInsetBound) return;
  entryDetailInsetBound = false;
  window.removeEventListener("resize", syncEntryDetailInset);
  entryDetailInsetRo?.disconnect();
  entryDetailInsetRo = null;
  document.documentElement.classList.remove("has-entry-detail-open");
  document.documentElement.style.removeProperty("--entry-detail-inset-top");
}

function ensureEntryDetailUi() {
  if (entryDetailUi) return entryDetailUi;
  entryDetailUi = createEntryDetailPanel(document.body, {
    lang: getLang(),
    onClose: () => closeEntryDetail(),
    onRelationPick: (literal) => handleEntryPick({ literal, fromRelationChip: true }),
  });
  return entryDetailUi;
}

let disconnectInfiniteScroll = null;

function remountInfiniteScroll() {
  disconnectInfiniteScroll?.();
  const root = $.searchResultsScroll || null;
  disconnectInfiniteScroll = wireInfiniteScroll({
    root,
    sentinel: $.resultsScrollSentinel,
    onNeedMore: handleInfiniteScrollNeed,
  });
}

function syncEntryDetailLayout() {
  const open = Boolean(shell.entryDetail.open);
  $.searchView?.classList.toggle("has-entry-detail", open);
  $.appShell?.classList.toggle("has-entry-detail", open);
  remountInfiniteScroll();
}

function closeEntryDetail() {
  shell.entryDetail.open = false;
  shell.entryDetail.activeLiteral = null;
  shell.entryDetail.preferredJyutping = null;
  ensureEntryDetailUi().close();
  syncEntryDetailLayout();
  unbindEntryDetailInset();
}

function openEntryDetail(literal, preferredJyutping, readings) {
  shell.entryDetail.open = true;
  shell.entryDetail.activeLiteral = literal;
  shell.entryDetail.preferredJyutping = preferredJyutping ?? null;
  syncEntryDetailLayout();
  bindEntryDetailInset();
  syncEntryDetailInset();
  const ui = ensureEntryDetailUi();
  const instant = readings?.length ? buildEntryDetailModelFromPick(literal, readings) : null;
  if (instant) ui.setModel(instant, preferredJyutping);
  else ui.showPending(literal);
  void fetchEntryDetail(literal).then((model) => {
    if (model && shell.entryDetail.activeLiteral === literal) {
      ensureEntryDetailUi().setModel(model, preferredJyutping);
    }
  });
}

async function handleEntryPick(payload) {
  if (shell.currentMode === "syn") {
    handleResultClick(payload.literal);
    return;
  }
  const action = resolveListClickAction({
    panelOpen: shell.entryDetail.open,
    activeLiteral: shell.entryDetail.activeLiteral,
    targetLiteral: payload.literal,
    fromRelationChip: payload.fromRelationChip,
  });
  if (action === "close") {
    closeEntryDetail();
    return;
  }
  if (action === "open_only") {
    shell.entryDetail.open = true;
    shell.entryDetail.activeLiteral = payload.literal;
    shell.entryDetail.preferredJyutping = payload.jyutping ?? null;
    syncEntryDetailLayout();
    return;
  }
  const tab = ensureActiveSearchTab();
  if (!tab) return;
  const literal = payload.literal.trim();
  shell.pickAnchor = literal;
  shell.pickAnchorRows = payload.readings?.length
    ? pickReadingsToQueryRows(literal, payload.readings)
    : anchorOnlyQueryRow(literal);
  Object.assign(tab, withResultClickQuery(tab, literal));
  tab.results = shell.pickAnchorRows;
  tab.offset = 0;
  tab.total = null;
  $.searchInput.value = literal;
  persistTabs();
  $.results.className = "results";
  renderMergedResultList($.results, tab.results, {
    lang: getLang(),
    activeLiteral: shell.entryDetail.activeLiteral,
    onPick: handleEntryPick,
  });
  const statsLabel = getModeMeta(shell.currentMode, getLang()).statsLabel;
  $.stats.textContent = `1 個結果（${statsLabel}）`;
  updateShuffleButton();
  searchDict();
  openEntryDetail(literal, payload.jyutping, payload.readings);
}

function createResultLink(text, query, title = "") {
  const link = document.createElement("a");
  link.className = "result-item";
  link.href = buildResultSearchHref({
    pathname: window.location.pathname,
    query,
    mode: shell.currentMode,
  });
  link.textContent = text;
  if (title) link.title = title;
  link.addEventListener("click", (event) => {
    event.preventDefault();
    handleResultClick(query);
  });
  link.setAttribute("aria-label", `搜尋 ${text}`);
  return link;
}

function handleResultClick(queryText) {
  const tab = ensureActiveSearchTab();
  if (!tab) return;
  Object.assign(tab, withResultClickQuery(tab, queryText));
  $.searchInput.value = queryText;
  persistTabs();
  searchDict();
}

function updateShuffleButton() {
  const tab = activeTab();
  const results = tab?.view === VIEW.SEARCH ? tab.results || [] : [];
  $.shuffleBtn.disabled = !results.length || tab?.view !== VIEW.SEARCH;
}

function shuffleResults() {
  const tab = activeTab();
  if (!tab || tab.view !== VIEW.SEARCH || !tab.results?.length) return;
  const shuffled = tab.results.slice();
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  tab.results = shuffled;
  resetRenderedCount(tab, countSearchResultItems(shuffled));
  persistTabs();
  renderSearchResults(tab.results);
}

function maybeModeRedirectForRelationSyntax(input, tab) {
  if (shell.currentMode !== "syn" || !isRelationSyntaxQuery(input)) return;
  const target = MODE_META[shell.last0243Mode] ? shell.last0243Mode : "m1";
  tab.offset = 0;
  tab.redirectHint = modeRedirectHint(target, getLang());
  if (shell.currentMode !== target) {
    shell.currentMode = target;
    updateModeLabel();
  }
}

function maybeModeRedirectForPingZeSerial(input, tab) {
  if (!isPingZeSerialQuery(input)) return;
  const effective = pingZeEffectiveMode();
  if (shell.currentMode === effective) return;
  tab.offset = 0;
  tab.redirectHint = pingZeModeRedirectHint(getLang());
  shell.currentMode = effective;
  updateModeLabel();
}

function decodeSearchHintHeader(raw) {
  if (!raw) return raw;
  const prefix = "UTF-8''";
  if (raw.startsWith(prefix)) {
    try {
      return decodeURIComponent(raw.slice(prefix.length));
    } catch {
      return raw;
    }
  }
  return raw;
}

function applyEffectiveModeFromResponse(res, searchHint) {
  const effectiveMode = res.headers.get("X-Effective-Mode");
  if (!effectiveMode || !MODE_META[effectiveMode] || effectiveMode === shell.currentMode) {
    return searchHint;
  }
  shell.currentMode = effectiveMode;
  updateModeLabel();
  updateBrowserUrlFromActiveTab(true);
  return searchHint || modeRedirectHint(effectiveMode, getLang());
}

function renderSearchResults(data, total = null, { expandFrom = null } = {}) {
  const tab = activeTab();
  const itemCount = countSearchResultItems(data);
  if (tab && tab.renderedCount == null) resetRenderedCount(tab, itemCount);
  const budget = tab ? effectiveRenderedCount(tab, itemCount) : itemCount;

  if (
    expandFrom != null &&
    expandFrom < budget &&
    isStandardWordListLayout(data) &&
    !tab?.redirectHint
  ) {
    const ul = $.results.querySelector("ul.results-list-items");
    const merged = mergedWordGroups(data);
    if (
      ul &&
      ul.dataset.resultLen === String(data.length) &&
      Number(ul.dataset.mergedLen) === merged.length
    ) {
      appendWordListSlice(ul, merged, expandFrom, budget, getLang());
      updateWordListStats(merged.length, total, data.length);
      updateShuffleButton();
      updateScrollSentinel(tab);
      return;
    }
  }

  $.results.innerHTML = "";
  const redirectHint = tab?.redirectHint;
  if (redirectHint) {
    const banner = document.createElement("p");
    banner.className = "info mode-redirect-hint";
    banner.textContent = redirectHint;
    $.results.appendChild(banner);
    tab.redirectHint = null;
  }
  $.results.className = shell.currentMode === "syn" ? "syn-container" : "results";

  if (shell.currentMode === "syn") {
    const syns = data.filter((r) => r.relation === "syn");
    const ants = data.filter((r) => r.relation === "ant");
    const related = data.filter((r) => r.relation === "semantic_related");
    const { synsShown, antsShown, relatedShown } = takeSynBudget(syns, ants, related, budget);
    $.results.appendChild(createSynSection("近義詞", synsShown));
    $.results.appendChild(createSynSection("反義詞", antsShown));
    if (related.length) $.results.appendChild(createSynSection("語意相關", relatedShown));
    $.stats.textContent = `近義 ${syns.length}　反義 ${ants.length}${related.length ? `　語意相關 ${related.length}` : ""}（已載入 ${data.length}）`;
    updateShuffleButton();
    updateScrollSentinel(tab);
    return;
  }

  const initialHits = data.filter((r) => r.anchor_dimension === "initial");
  const finalHits = data.filter((r) => r.anchor_dimension === "final");
  if (initialHits.length || finalHits.length) {
    $.results.className = "syn-container";
    const initialMerged = mergeResultsByLiteral(
      initialHits.map((row) => ({ ...row, word: row.char || row.display_text })),
    );
    const finalMerged = mergeResultsByLiteral(
      finalHits.map((row) => ({ ...row, word: row.char || row.display_text })),
    );
    const initialShown = initialMerged.slice(0, budget);
    const finalShown = finalMerged.slice(0, Math.max(0, budget - initialShown.length));
    $.results.appendChild(createAnchorSectionFromGroups("聲母", initialShown));
    $.results.appendChild(createAnchorSectionFromGroups("韻母", finalShown));
    $.stats.textContent = `聲母 ${initialHits.length}　韻母 ${finalHits.length}（已載入 ${data.length}）`;
    updateShuffleButton();
    updateScrollSentinel(tab);
    return;
  }

  const merged = mergedWordGroups(data);
  const ul = document.createElement("ul");
  ul.className = "results-list-items";
  ul.dataset.resultLen = String(data.length);
  ul.dataset.mergedLen = String(merged.length);
  appendWordListSlice(ul, merged, 0, budget, getLang());
  $.results.appendChild(ul);
  updateWordListStats(merged.length, total, data.length);
  updateShuffleButton();
  updateScrollSentinel(tab);
}

function createAnchorSectionFromGroups(title, groups) {
  const section = document.createElement("section");
  section.className = "syn-section";
  const heading = document.createElement("h2");
  heading.textContent = `${title}${groups.length ? ` (${groups.length})` : ""}`;
  section.appendChild(heading);
  const ul = document.createElement("ul");
  ul.className = "results-list-items";
  const lang = getLang();
  groups.forEach((group) =>
    ul.appendChild(
      createMergedResultButton(group, {
        lang,
        activeLiteral: shell.entryDetail.activeLiteral,
        onPick: handleEntryPick,
      }),
    ),
  );
  section.appendChild(ul);
  return section;
}

function createSynSection(title, items) {
  const section = document.createElement("section");
  section.className = "syn-section";
  const heading = document.createElement("h2");
  heading.textContent = `${title}${items.length ? ` (${items.length})` : ""}`;
  section.appendChild(heading);

  const grid = document.createElement("div");
  grid.className = "results";
  if (items.length) {
    items.forEach((item) => {
      const char = item && typeof item === "object" ? item.char || "" : String(item || "");
      const source = item && typeof item === "object" && item.source ? `來源：${item.source}` : "";
      const inDb = item && typeof item === "object" && item.in_db === false ? "外部詞庫" : "";
      if (char) grid.appendChild(createResultLink(char, char, [source, inDb].filter(Boolean).join(" · ")));
    });
  } else {
    const empty = document.createElement("p");
    empty.className = "syn-empty";
    empty.textContent = "無可用結果";
    grid.appendChild(empty);
  }
  section.appendChild(grid);
  return section;
}

function finishSearchWithData(tab, data, { append = false, total = null } = {}) {
  let displayData;
  const pickAnchor = shell.pickAnchor;
  if (!append && pickAnchor && (tab.q || "").trim() === pickAnchor) {
    displayData = mergePickLookupResults(pickAnchor, shell.pickAnchorRows || [], data);
    tab.results = displayData;
    tab.offset = displayData.length;
    if (total != null) tab.total = total;
    persistTabs();
    appendPickLookupTail($.results, pickAnchor, displayData, {
      lang: getLang(),
      activeLiteral: shell.entryDetail.activeLiteral,
      onPick: handleEntryPick,
    });
    const statsLabel = getModeMeta(shell.currentMode, getLang()).statsLabel;
    if (tab.total != null && tab.total > displayData.length) {
      $.stats.textContent = `已載入 ${displayData.length} / ${tab.total} 個結果（${statsLabel}）`;
    } else if (tab.total != null) {
      $.stats.textContent = `${tab.total} 個結果（${statsLabel}）`;
    } else {
      $.stats.textContent = `${displayData.length} 個結果（${statsLabel}）`;
    }
    shell.pickAnchor = null;
    shell.pickAnchorRows = null;
    updateShuffleButton();
    updateScrollSentinel(tab);
    return;
  }
  displayData = append ? (tab.results || []).concat(data) : data;
  tab.results = displayData;
  tab.offset = (tab.offset || 0) + data.length;
  if (!append && total != null) tab.total = total;
  const itemCount = countSearchResultItems(displayData);
  if (append) {
    persistTabs();
    const ul = $.results.querySelector("ul.results-list-items");
    if (ul && isStandardWordListLayout(displayData)) {
      const merged = mergedWordGroups(displayData);
      ul.dataset.resultLen = String(displayData.length);
      ul.dataset.mergedLen = String(merged.length);
      updateWordListStats(merged.length, tab.total, displayData.length);
      updateShuffleButton();
      updateScrollSentinel(tab);
      return;
    }
    renderSearchResults(displayData, tab.total);
    return;
  }
  resetRenderedCount(tab, itemCount);
  persistTabs();
  renderSearchResults(displayData, tab.total);
  remountInfiniteScroll();
}

async function searchDict(isLoadMore = false, restoreFromHistory = false) {
  if (!shell.appSearchReady) return;
  const tab = ensureActiveSearchTab();
  if (!tab) return;

  shell.searchAbort?.abort();
  shell.searchAbort = new AbortController();
  const { signal } = shell.searchAbort;

  const input = $.searchInput.value.trim();
  if (!isLoadMore && input && input !== shell.pickAnchor) {
    shell.pickAnchor = null;
    shell.pickAnchorRows = null;
  }
  if (!isLoadMore && input) tab.q = input;
  if (!restoreFromHistory) showSearch({ replace: true });
  const staleResults = !isLoadMore && (tab.results?.length > 0);
  setButtonLoading(true, { staleResults });

  // 新搜尋：API 窗口永遠 offset=0（P3 可保留舊列 UI，但唔沿用上一查嘅已擷取位移）
  if (!isLoadMore) {
    tab.offset = 0;
    tab.total = null;
    if (!staleResults) {
      $.results.innerHTML = "";
      $.stats.textContent = "";
      tab.results = [];
      updateScrollSentinel(tab);
    }
  }

  if (!input) {
    $.results.innerHTML = '<p class="info"><strong>請輸入搜尋內容。</strong><br>例如 <code translate="no">香??</code>、<code translate="no">23+就=</code>、<code translate="no">?=就</code> 或 <code translate="no">香港=</code>。</p>';
    tab.q = "";
    persistTabs();
    updateShuffleButton();
    setButtonLoading(false);
    return;
  }

  if (!isLoadMore && isCorrectionsSearchCommand(input)) {
    showCorrections({ replace: true });
    setButtonLoading(false);
    return;
  }

  tab.q = input;
  if (!isLoadMore) {
    maybeModeRedirectForRelationSyntax(input, tab);
    maybeModeRedirectForPingZeSerial(input, tab);
  }
  if (!restoreFromHistory && !isLoadMore) {
    const { pushed } = commitSearchHistoryFrame(tab, { q: input, mode: shell.currentMode });
    updateBrowserUrlFromActiveTab(!pushed);
  }

  const offset = isLoadMore ? tab.offset || 0 : 0;
  const pageSize = searchLimitForOffset(shell.currentMode, offset);
  const cacheKey = `${shell.currentMode}:${input}:${offset}:${pageSize}`;
  if (!isLoadMore && searchCache.has(cacheKey)) {
    const cached = searchCache.get(cacheKey);
    if (Array.isArray(cached)) {
      if (cached.length === 0) {
        searchCache.delete(cacheKey);
      } else {
        finishSearchWithData(tab, cached, { append: false });
        setButtonLoading(false);
        return;
      }
    } else if (cached && Array.isArray(cached.data)) {
      // F2: 唔信空 cache（可能係錯 offset 時代寫入嘅假空）
      if (cached.data.length === 0) {
        searchCache.delete(cacheKey);
      } else {
        finishSearchWithData(tab, cached.data, { append: false, total: cached.total });
        setButtonLoading(false);
        return;
      }
    } else {
      searchCache.delete(cacheKey);
    }
  }

  let url = `/words/search/?q=${encodeURIComponent(input)}&mode=${encodeURIComponent(shell.currentMode)}&limit=${pageSize}&offset=${offset}`;
  if (shell.currentMode === "syn" && MODE_META[shell.last0243Mode]) {
    url += `&fallback_0243_mode=${encodeURIComponent(shell.last0243Mode)}`;
  }

  try {
    const res = await fetch(url, { signal });
    if (res.status === 503) {
      const snap = await res.json().catch(() => null);
      if (snap && !snap.gate_ready) {
        setGateInkProgress(wordCacheProgress(snap));
        const pct = Math.round(wordCacheProgress(snap) * 100);
        $.results.innerHTML = `<p class="info"><strong>仲未開得工…</strong><br>詞庫快取索引載入中（${pct}%）。請稍候再搜。</p>`;
        updateShuffleButton();
        updateScrollSentinel(tab);
        return;
      }
    }
    if (!res.ok) throw new Error(`後端回應失敗 (${res.status})`);
    const data = await res.json();
    const totalHeader = res.headers.get("X-Search-Total");
    const total = totalHeader ? Number.parseInt(totalHeader, 10) : null;
    let searchHint = decodeSearchHintHeader(res.headers.get("X-Search-Hint"));
    searchHint = applyEffectiveModeFromResponse(res, searchHint);
    if (!searchHint && tab.redirectHint) {
      searchHint = tab.redirectHint;
    }

    // F2: 只 cache 非空首頁，避免假空結果卡死
    if (!isLoadMore && data.length > 0) {
      searchCache.set(cacheKey, { data, total, hint: searchHint });
      if (searchCache.size > 50) searchCache.delete(searchCache.keys().next().value);
    }

    if (data.length === 0 && !isLoadMore) {
      const hint = tab.redirectHint || searchHint;
      tab.redirectHint = null;
      tab.results = [];
      tab.offset = 0;
      $.results.innerHTML = emptySearchResultsHtml(input, hint, shell.currentMode);
      updateShuffleButton();
      updateScrollSentinel(tab);
      return;
    }

    finishSearchWithData(tab, data, { append: isLoadMore, total: isLoadMore ? null : total });
  } catch (error) {
    if (error?.name === "AbortError") return;
    console.error(error);
    const isHttp = error instanceof Error && /後端回應失敗/.test(error.message);
    if (isHttp) {
      $.results.innerHTML = `<p class="info info-error"><strong>搜尋失敗（${escapeHtml(error.message)}）。</strong><br>後端已連線但處理請求時出錯；請重啟 <code translate="no">start.sh</code> 後再試。</p>`;
    } else {
      $.results.innerHTML = '<p class="info info-error"><strong>無法連接到後端。</strong><br>請確認已執行 <code translate="no">start.sh</code> 並透過 <code translate="no">http://127.0.0.1:8000/frontend/index.html</code> 開啟（勿直接開檔案）。</p>';
    }
    updateShuffleButton();
    updateScrollSentinel(tab);
  } finally {
    if (!signal.aborted) setButtonLoading(false);
  }
}

function wireEntryDetailKeyboard() {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && shell.entryDetail.open) {
      closeEntryDetail();
    }
  });
  $.searchViewMain?.addEventListener("click", (event) => {
    if (!shell.entryDetail.open) return;
    if (event.target.closest(".entry-detail-panel")) return;
    if (event.target.closest(".result-link")) return;
    closeEntryDetail();
  });
}

wireEntryDetailKeyboard();

document.getElementById("loadMoreBtn")?.remove();
remountInfiniteScroll();

export {
  applyEffectiveModeFromResponse,
  closeEntryDetail,
  finishSearchWithData,
  handleEntryPick,
  renderSearchResults,
  runExample,
  searchDict,
  shouldShowLoadMore,
  shuffleResults,
  switchMode,
  toggleMenu,
  updateModeLabel,
  updateShuffleButton,
  wireModeMenuKeyboard,
};
