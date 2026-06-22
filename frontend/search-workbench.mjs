import { isRelationSyntaxQuery, modeRedirectHint } from "./relation-syntax.mjs";
import { escapeHtml, escapeHtmlAttr } from "./dom-escape.mjs";
import {
  $,
  MODE_META,
  PAGE_SIZE,
  shell,
  searchCache,
  VIEW,
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
  withResultClickQuery,
} from "./search-navigation.mjs";

function emptySearchResultsHtml(input, hint, mode) {
  const q = escapeHtml(input);
  if (mode === "m1" || mode === "m2") {
    if (hint) {
      return `<p class="info"><strong>搵唔到</strong><br>${escapeHtml(hint)}</p>`;
    }
    return `<p class="info"><strong>搵唔到「${q}」。</strong></p>`;
  }
  if (hint) {
    return `<p class="info"><strong>找不到「${q}」。</strong><br>${escapeHtml(hint)}</p>`;
  }
  return `<p class="info"><strong>找不到「${q}」。</strong><br>試試改用較短的詞、加上 <code translate="no">=</code> 查韻，或切換搜尋模式。</p>`;
}

function shouldShowLoadMore(tab) {
  const results = tab.results || [];
  const total = tab.total;
  return (total != null && results.length < total) || results.length >= PAGE_SIZE;
}

function setButtonLoading(loading) {
  shell.isSearching = loading;
  $.searchBtn.disabled = loading || !shell.appSearchReady;
  $.searchBtn.textContent = loading ? "搜尋中…" : "搜尋";
}

function updateModeLabel() {
  const meta = MODE_META[shell.currentMode] || MODE_META.m1;
  $.currentModeLabel.innerHTML =
    `<span class="mode-trigger-primary">${meta.title}</span><span class="mode-trigger-note">${meta.note}</span>`;
  $.modeReadout.textContent = `目前模式：${meta.readout}`;
  $.searchInput.placeholder = meta.placeholder;
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
  if (mode === "syn" && (shell.currentMode === "m1" || shell.currentMode === "m2")) {
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
  showSearch({ replace: true });
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
  persistTabs();
  renderSearchResults(tab.results);
}

function maybeModeRedirectForRelationSyntax(input, tab) {
  if (shell.currentMode !== "syn" || !isRelationSyntaxQuery(input)) return;
  const target = MODE_META[shell.last0243Mode] ? shell.last0243Mode : "m1";
  tab.offset = 0;
  tab.redirectHint = modeRedirectHint(target);
  if (shell.currentMode !== target) {
    shell.currentMode = target;
    updateModeLabel();
  }
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
  return searchHint || modeRedirectHint(effectiveMode);
}

function renderSearchResults(data, total = null) {
  $.results.innerHTML = "";
  const tab = activeTab();
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
    $.results.appendChild(createSynSection("近義詞", syns));
    $.results.appendChild(createSynSection("反義詞", ants));
    if (related.length) $.results.appendChild(createSynSection("語意相關", related));
    $.stats.textContent = `近義 ${syns.length}　反義 ${ants.length}${related.length ? `　語意相關 ${related.length}` : ""}（已載入 ${data.length}）`;
    updateShuffleButton();
    return;
  }

  const initialHits = data.filter((r) => r.anchor_dimension === "initial");
  const finalHits = data.filter((r) => r.anchor_dimension === "final");
  if (initialHits.length || finalHits.length) {
    $.results.className = "syn-container";
    $.results.appendChild(createSynSection("聲母", initialHits));
    $.results.appendChild(createSynSection("韻母", finalHits));
    $.stats.textContent = `聲母 ${initialHits.length}　韻母 ${finalHits.length}（已載入 ${data.length}）`;
    updateShuffleButton();
    return;
  }

  const frag = document.createDocumentFragment();
  const seen = new Set();
  const deduped = [];
  data.forEach((word) => {
    const ch = word.display_text || word.char;
    if (!ch || seen.has(ch)) return;
    seen.add(ch);
    deduped.push(word);
  });

  deduped.forEach((word) => {
    const display = word.display_text || word.char;
    const qtext = word.query_text || word.char;
    frag.appendChild(createResultLink(display, qtext, word.jyutping || ""));
  });
  $.results.appendChild(frag);
  $.stats.textContent = `${deduped.length} 個結果（${MODE_META[shell.currentMode].statsLabel}）`;
  if (total != null && total > deduped.length) {
    $.stats.textContent = `已載入 ${deduped.length} / ${total} 個結果（${MODE_META[shell.currentMode].statsLabel}）`;
  } else if (total != null) {
    $.stats.textContent = `${total} 個結果（${MODE_META[shell.currentMode].statsLabel}）`;
  }
  updateShuffleButton();
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

function toggleLoadMoreButton(show) {
  let btn = document.getElementById("loadMoreBtn");
  if (!btn) {
    btn = document.createElement("button");
    btn.id = "loadMoreBtn";
    btn.type = "button";
    btn.textContent = "載入更多";
    btn.className = "load-more";
    btn.addEventListener("click", () => searchDict(true));
    $.results.after(btn);
  }
  const tab = activeTab();
  btn.hidden = !show || tab?.view !== VIEW.SEARCH;
}

function finishSearchWithData(tab, data, { append = false, total = null } = {}) {
  const displayData = append ? (tab.results || []).concat(data) : data;
  tab.results = displayData;
  tab.offset = (tab.offset || 0) + data.length;
  if (!append && total != null) tab.total = total;
  persistTabs();
  renderSearchResults(displayData, tab.total);
  const hasMore = (tab.total != null && displayData.length < tab.total) || data.length === PAGE_SIZE;
  toggleLoadMoreButton(hasMore);
}

async function searchDict(isLoadMore = false, restoreFromHistory = false) {
  if (!shell.appSearchReady) return;
  const tab = ensureActiveSearchTab();
  if (!tab) return;

  shell.searchAbort?.abort();
  shell.searchAbort = new AbortController();
  const { signal } = shell.searchAbort;

  showSearch({ replace: true });
  setButtonLoading(true);

  const input = $.searchInput.value.trim();

  if (!isLoadMore) {
    $.results.innerHTML = "";
    $.stats.textContent = "";
    tab.results = [];
    tab.offset = 0;
    tab.total = null;
    toggleLoadMoreButton(false);
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
  }
  if (!restoreFromHistory && !isLoadMore) updateBrowserUrlFromActiveTab(false);

  const cacheKey = `${shell.currentMode}:${input}:${tab.offset || 0}`;
  if (!isLoadMore && searchCache.has(cacheKey)) {
    const cached = searchCache.get(cacheKey);
    if (Array.isArray(cached)) {
      finishSearchWithData(tab, cached, { append: false });
      setButtonLoading(false);
      return;
    }
    if (cached && Array.isArray(cached.data)) {
      if (cached.data.length === 0) {
        $.results.innerHTML = emptySearchResultsHtml(input, cached.hint, shell.currentMode);
        updateShuffleButton();
        setButtonLoading(false);
        toggleLoadMoreButton(false);
        return;
      }
      finishSearchWithData(tab, cached.data, { append: false, total: cached.total });
      setButtonLoading(false);
      return;
    }
    searchCache.delete(cacheKey);
  }

  let url = `/words/search/?q=${encodeURIComponent(input)}&mode=${encodeURIComponent(shell.currentMode)}&limit=${PAGE_SIZE}&offset=${tab.offset || 0}`;
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
        toggleLoadMoreButton(false);
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

    if (!isLoadMore) {
      searchCache.set(cacheKey, { data, total, hint: searchHint });
      if (searchCache.size > 50) searchCache.delete(searchCache.keys().next().value);
    }

    if (data.length === 0 && !isLoadMore) {
      const hint = tab.redirectHint || searchHint;
      tab.redirectHint = null;
      $.results.innerHTML = emptySearchResultsHtml(input, hint, shell.currentMode);
      updateShuffleButton();
      toggleLoadMoreButton(false);
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
    toggleLoadMoreButton(false);
  } finally {
    if (!signal.aborted) setButtonLoading(false);
  }
}

export {
  applyEffectiveModeFromResponse,
  finishSearchWithData,
  renderSearchResults,
  runExample,
  searchDict,
  shouldShowLoadMore,
  shuffleResults,
  switchMode,
  toggleLoadMoreButton,
  toggleMenu,
  updateModeLabel,
  updateShuffleButton,
  wireModeMenuKeyboard,
};
