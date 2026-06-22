import { $, shell } from "./app-context.mjs";

const DEBOUNCE_MS = 250;
let explainTimer = null;
let explainAbort = null;

function clearQueryExplain() {
  if (!$.queryExplain) return;
  $.queryExplain.hidden = true;
  if ($.queryExplainSummary) $.queryExplainSummary.textContent = "";
  if ($.queryExplainWarning) {
    $.queryExplainWarning.textContent = "";
    $.queryExplainWarning.hidden = true;
  }
}

function renderQueryExplain({ summary, warning }) {
  if (!$.queryExplain) return;
  const hasSummary = Boolean(summary);
  const hasWarning = Boolean(warning);
  if (!hasSummary && !hasWarning) {
    clearQueryExplain();
    return;
  }
  if ($.queryExplainSummary) {
    $.queryExplainSummary.textContent = summary || "";
  }
  if ($.queryExplainWarning) {
    if (hasWarning) {
      $.queryExplainWarning.textContent = warning;
      $.queryExplainWarning.hidden = false;
    } else {
      $.queryExplainWarning.textContent = "";
      $.queryExplainWarning.hidden = true;
    }
  }
  $.queryExplain.hidden = false;
}

async function refreshQueryExplain(input = $.searchInput?.value ?? "") {
  const q = (input || "").trim();
  if (!q) {
    if (explainAbort) explainAbort.abort();
    clearQueryExplain();
    return;
  }
  if (explainAbort) explainAbort.abort();
  explainAbort = new AbortController();
  const signal = explainAbort.signal;
  try {
    const params = new URLSearchParams({
      q,
      mode: shell.currentMode,
    });
    const res = await fetch(`/words/query/explain?${params.toString()}`, { signal });
    if (!res.ok) return;
    const data = await res.json();
    if (signal.aborted) return;
    renderQueryExplain(data);
  } catch (err) {
    if (err?.name === "AbortError") return;
  }
}

function scheduleQueryExplain(input = $.searchInput?.value ?? "") {
  if (explainTimer) clearTimeout(explainTimer);
  explainTimer = setTimeout(() => {
    explainTimer = null;
    refreshQueryExplain(input);
  }, DEBOUNCE_MS);
}

export {
  clearQueryExplain,
  refreshQueryExplain,
  scheduleQueryExplain,
};