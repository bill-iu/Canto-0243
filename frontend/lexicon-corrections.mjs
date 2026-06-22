import { $, VIEW } from "./app-context.mjs";

/** @type {Array<{char:string,code:string,jyutping:string,action:string,value:string,note:string}>} */
const sessionRows = [];
/** @type {{char:string,code:string,jyutping:string}|null} */
let selectedRow = null;
/** @type {string} */
let previewCode = "";
let wired = false;
/** @type {number|null} */
let mountedTabId = null;

function showCorrectionOk(text) {
  $.correctionOkStatus.textContent = text;
  $.correctionOkStatus.hidden = false;
  $.correctionErrStatus.hidden = true;
}

function showCorrectionErr(text) {
  $.correctionErrStatus.textContent = text;
  $.correctionErrStatus.hidden = false;
  $.correctionOkStatus.hidden = true;
}

function renderSessionList() {
  if (!sessionRows.length) {
    $.correctionSessionPanel.hidden = true;
    $.correctionSessionList.replaceChildren();
    return;
  }
  $.correctionSessionPanel.hidden = false;
  $.correctionSessionList.replaceChildren(
    ...sessionRows.map((row) => {
      const li = document.createElement("li");
      li.textContent = `${row.char} · code ${row.code} · ${row.jyutping} → ${row.action} ${row.value}${row.note ? `（${row.note}）` : ""}`;
      return li;
    })
  );
}

function clearRowSelection() {
  selectedRow = null;
  previewCode = "";
  $.correctionsSubmitForm.hidden = true;
  $.correctionCodePreview.hidden = true;
  $.correctionNewJyutping.value = "";
}

function renderRowChoices(rows) {
  $.correctionRowList.replaceChildren();
  if (!rows.length) {
    $.correctionRowsPanel.hidden = true;
    showCorrectionErr("詞庫中找不到此字面。");
    clearRowSelection();
    return;
  }
  $.correctionRowsPanel.hidden = false;
  rows.forEach((row, index) => {
    const id = `correction-row-${index}`;
    const label = document.createElement("label");
    label.className = "corrections-row-choice";
    label.htmlFor = id;
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "correction_row";
    input.id = id;
    input.value = String(index);
    input.addEventListener("change", () => selectRow(row));
    const text = document.createElement("span");
    text.textContent = `code ${row.code} · ${row.jyutping}`;
    label.append(input, text);
    $.correctionRowList.append(label);
  });
}

async function refreshCodePreview(jyutping) {
  const literal = (jyutping || "").trim();
  if (!literal || !selectedRow) {
    $.correctionCodePreview.hidden = true;
    previewCode = "";
    return;
  }
  try {
    const res = await fetch(`/lexicon/code-preview?jyutping=${encodeURIComponent(literal)}`);
    if (!res.ok) throw new Error("preview failed");
    const body = await res.json();
    previewCode = body.code || "";
    $.correctionCodePreview.textContent = `依粵拼應為 code ${previewCode}（現有 ${selectedRow.code}）`;
    $.correctionCodePreview.hidden = !previewCode || previewCode === selectedRow.code;
  } catch {
    previewCode = "";
    $.correctionCodePreview.hidden = true;
  }
}

function selectRow(row) {
  selectedRow = { char: row.char, code: row.code, jyutping: row.jyutping };
  $.correctionsSubmitForm.hidden = false;
  $.correctionNewJyutping.value = row.jyutping || "";
  $.correctionNote.value = "";
  $.correctionOkStatus.hidden = true;
  $.correctionErrStatus.hidden = true;
  refreshCodePreview(row.jyutping);
}

async function lookupRows(char) {
  const literal = char.trim();
  if (!literal) {
    showCorrectionErr("請輸入字面。");
    return;
  }
  $.correctionLookupBtn.disabled = true;
  $.correctionOkStatus.hidden = true;
  $.correctionErrStatus.hidden = true;
  clearRowSelection();
  try {
    const res = await fetch(`/words/rows?char=${encodeURIComponent(literal)}`);
    if (!res.ok) throw new Error("lookup failed");
    const rows = await res.json();
    renderRowChoices(rows);
    if (rows.length === 1) {
      const only = $.correctionRowList.querySelector('input[type="radio"]');
      if (only) {
        only.checked = true;
        selectRow(rows[0]);
      }
    }
  } catch {
    showCorrectionErr("無法連線後端。請確認伺服器已啟動。");
    $.correctionRowsPanel.hidden = true;
  } finally {
    $.correctionLookupBtn.disabled = false;
  }
}

async function submitCorrection(action, value) {
  if (!selectedRow) {
    showCorrectionErr("請先選取收錄列。");
    return;
  }
  $.correctionJyutpingBtn.disabled = true;
  $.correctionRecalcCodeBtn.disabled = true;
  try {
    const res = await fetch("/lexicon/corrections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        char: selectedRow.char,
        code: selectedRow.code,
        jyutping: selectedRow.jyutping,
        action,
        value,
        note: $.correctionNote.value.trim(),
      }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      showCorrectionErr(body.detail || "提交失敗。");
      return;
    }
    sessionRows.unshift({
      char: body.char,
      code: body.code,
      jyutping: body.jyutping,
      action: body.action,
      value: body.value,
      note: body.note || "",
    });
    renderSessionList();
    showCorrectionOk(`${body.message} 搜尋結果待套用後更新。`);
  } catch {
    showCorrectionErr("無法連線後端。請確認伺服器已啟動。");
  } finally {
    $.correctionJyutpingBtn.disabled = false;
    $.correctionRecalcCodeBtn.disabled = false;
  }
}

function wireCorrectionsForm() {
  if (!$.correctionsLookupForm || wired) return;
  wired = true;

  $.correctionsLookupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    lookupRows($.correctionChar.value);
  });

  $.correctionNewJyutping?.addEventListener("input", () => {
    refreshCodePreview($.correctionNewJyutping.value);
  });

  $.correctionJyutpingBtn?.addEventListener("click", async () => {
    const next = $.correctionNewJyutping.value.trim();
    if (!next) {
      showCorrectionErr("請填寫新粵拼。");
      return;
    }
    if (selectedRow && next === selectedRow.jyutping) {
      showCorrectionErr("新粵拼與現有相同。");
      return;
    }
    await submitCorrection("set_jyutping", next);
  });

  $.correctionRecalcCodeBtn?.addEventListener("click", async () => {
    if (!selectedRow) return;
    await refreshCodePreview(selectedRow.jyutping);
    if (!previewCode) {
      showCorrectionErr("無法計算 code。");
      return;
    }
    if (previewCode === selectedRow.code) {
      showCorrectionErr("code 與粵拼已一致，無需重算。");
      return;
    }
    await submitCorrection("set_code", previewCode);
  });
}

function mountCorrectionsPanel(tab) {
  if (!tab || tab.view !== VIEW.CORRECTIONS) return;
  wireCorrectionsForm();
  const prefetch = (tab.prefetchChar || "").trim();
  if (mountedTabId !== tab.id) {
    mountedTabId = tab.id;
    $.correctionChar.value = prefetch;
    clearRowSelection();
    $.correctionRowsPanel.hidden = true;
    $.correctionOkStatus.hidden = true;
    $.correctionErrStatus.hidden = true;
    if (prefetch) lookupRows(prefetch);
  }
  $.correctionChar?.focus({ preventScroll: true });
}

export { mountCorrectionsPanel };
