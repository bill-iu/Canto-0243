import { escapeHtml } from './dom-escape.mjs';
import { tDetail } from './entry-detail-i18n.mjs';
import {
  mergeResultsByLiteral,
  resolveListClickAction,
  pickPreferredReadingIndex,
  buildEntryDetailModelFromPick,
} from './entry-detail-core.mjs';

export function createMergedResultButton(group, { lang, activeLiteral, onPick }) {
  const li = document.createElement('li');
  li.className = `result-item${activeLiteral === group.literal ? ' is-detail-active' : ''}`;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'result-link result-link--inline';
  const word = document.createElement('span');
  word.className = 'word result-literal-only';
  word.textContent = group.literal;
  btn.appendChild(word);
  if (group.readingCount > 1) {
    const badge = document.createElement('span');
    badge.className = 'result-reading-badge';
    badge.textContent = tDetail('detail.readings.n', lang, { n: group.readingCount });
    btn.appendChild(badge);
  }
  btn.addEventListener('click', (event) => {
    event.preventDefault();
    onPick({
      literal: group.literal,
      jyutping: group.readings[0]?.jyutping,
      readings: group.readings.map((r) => ({ jyutping: r.jyutping, code: r.code })),
    });
  });
  li.appendChild(btn);
  return li;
}

export function renderMergedResultList(container, rows, options) {
  const { lang, activeLiteral, onPick } = options;
  const merged = mergeResultsByLiteral(rows);
  const ul = document.createElement('ul');
  ul.className = 'results-list-items';
  merged.forEach((group) => ul.appendChild(createMergedResultButton(group, { lang, activeLiteral, onPick })));
  container.replaceChildren(ul);
}

/** Append lookup tail after pinned anchor — avoids full list DOM rebuild (ADR-0030 path A). */
export function appendPickLookupTail(container, anchorLiteral, mergedRows, options) {
  const anchor = String(anchorLiteral ?? '').trim();
  const rows = (mergedRows ?? []).map((row) => ({ ...row, word: row.word ?? row.char }));
  let ul = container.querySelector('.results-list-items');
  if (!ul) {
    renderMergedResultList(container, rows.filter((row) => String(row.word ?? '').trim() === anchor), options);
    ul = container.querySelector('.results-list-items');
    if (!ul) return;
  }
  const existing = new Set(
    [...ul.querySelectorAll('.result-literal-only')].map((el) => el.textContent?.trim() ?? ''),
  );
  for (const group of mergeResultsByLiteral(rows)) {
    if (group.literal === anchor || existing.has(group.literal)) continue;
    ul.appendChild(createMergedResultButton(group, options));
  }
}

export async function fetchEntryDetail(literal) {
  const res = await fetch(`/words/entry-detail/?char=${encodeURIComponent(literal)}`);
  if (!res.ok) return null;
  return res.json();
}

export function createEntryDetailPanel(host, { lang, onClose, onRelationPick }) {
  let model = null;
  let readingIdx = 0;

  const panel = document.createElement('aside');
  panel.className = 'entry-detail-panel';
  panel.hidden = true;
  host.appendChild(panel);

  function render() {
    if (!model) {
      panel.hidden = true;
      panel.innerHTML = '';
      return;
    }
    panel.hidden = false;
    const reading = model.readings[readingIdx] ?? model.readings[0];
    if (!reading) return;

    const tabs =
      model.readings.length > 1
        ? `<div class="entry-detail-reading-tabs" role="tablist">${model.readings
            .map(
              (_, i) =>
                `<button type="button" role="tab" class="entry-detail-reading-tab${
                  i === readingIdx ? ' is-active' : ''
                }" data-idx="${i}">${escapeHtml(tDetail('detail.reading', lang, { n: i + 1 }))}</button>`,
            )
            .join('')}</div>`
        : '';

    const sources = model.sources?.length
      ? model.sources.map((s) => `<span class="entry-detail-source-tag">${escapeHtml(s)}</span>`).join('')
      : `<span class="entry-detail-source-tag">${escapeHtml(tDetail('detail.noSources', lang))}</span>`;

    const syns = model.syns?.length
      ? `<section class="entry-detail-section"><h3 class="entry-detail-section__title">${escapeHtml(
          tDetail('detail.syns', lang),
        )}</h3><div class="entry-detail-chip-row">${model.syns
          .map(
            (w) =>
              `<button type="button" class="entry-detail-chip" data-rel="${escapeHtml(w)}">${escapeHtml(w)}</button>`,
          )
          .join('')}</div></section>`
      : '';

    const ants = model.ants?.length
      ? `<section class="entry-detail-section"><h3 class="entry-detail-section__title">${escapeHtml(
          tDetail('detail.ants', lang),
        )}</h3><div class="entry-detail-chip-row">${model.ants
          .map(
            (w) =>
              `<button type="button" class="entry-detail-chip" data-rel="${escapeHtml(w)}">${escapeHtml(w)}</button>`,
          )
          .join('')}</div></section>`
      : '';

    panel.innerHTML = `
      <header class="entry-detail-panel__header">
        <h2 class="entry-detail-panel__title">${escapeHtml(tDetail('detail.title', lang))}</h2>
        <button type="button" class="entry-detail-panel__close" aria-label="${escapeHtml(tDetail('detail.close', lang))}">×</button>
      </header>
      <div class="entry-detail-panel__body">
        <div class="entry-detail-panel__hero">
          <div class="entry-detail-panel__literal">${escapeHtml(model.literal)}</div>
          <div class="entry-detail-panel__actions">
            <button type="button" class="entry-detail-panel__icon-btn" data-copy>${escapeHtml(tDetail('detail.copy', lang))}</button>
          </div>
        </div>
        <p class="entry-detail-panel__jyutping">${escapeHtml(reading.jyutping)}</p>
        <span class="entry-detail-panel__code-pill">${escapeHtml(reading.code0243)}</span>
        ${tabs}
        <section class="entry-detail-section">
          <h3 class="entry-detail-section__title">${escapeHtml(tDetail('detail.phonetic', lang))}</h3>
          <div class="entry-detail-phonetic-grid">
            <div class="entry-detail-phonetic-card">
              <span class="entry-detail-phonetic-card__label">${escapeHtml(tDetail('detail.initials', lang))}</span>
              <span class="entry-detail-phonetic-card__value">${escapeHtml((reading.initials || []).join(' ') || '—')}</span>
            </div>
            <div class="entry-detail-phonetic-card">
              <span class="entry-detail-phonetic-card__label">${escapeHtml(tDetail('detail.finals', lang))}</span>
              <span class="entry-detail-phonetic-card__value">${escapeHtml((reading.finals || []).join(' ') || '—')}</span>
            </div>
          </div>
        </section>
        <section class="entry-detail-section">
          <h3 class="entry-detail-section__title">${escapeHtml(tDetail('detail.tone', lang))}</h3>
          <div class="entry-detail-tone-rows">
            <div class="entry-detail-tone-row"><span>${escapeHtml(tDetail('detail.tone.0243', lang))}</span><strong>${escapeHtml(reading.code0243)}</strong></div>
            <div class="entry-detail-tone-row"><span>${escapeHtml(tDetail('detail.tone.02493', lang))}</span><strong>${escapeHtml(reading.code02493)}</strong></div>
          </div>
        </section>
        <div class="entry-detail-meta-row"><span>${escapeHtml(tDetail('detail.length', lang))}</span><strong>${model.length}</strong></div>
        <div class="entry-detail-meta-row"><span>${escapeHtml(tDetail('detail.corpusWeight', lang))}</span><strong>${Number(model.corpusWeight || 0).toLocaleString()}</strong></div>
        <section class="entry-detail-section"><h3 class="entry-detail-section__title">${escapeHtml(tDetail('detail.sources', lang))}</h3>${sources}</section>
        ${syns}${ants}
      </div>`;

    panel.querySelector('.entry-detail-panel__close')?.addEventListener('click', onClose);
    panel.querySelector('[data-copy]')?.addEventListener('click', () => {
      navigator.clipboard?.writeText(model.literal).catch(() => {});
    });
    panel.querySelectorAll('.entry-detail-reading-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        readingIdx = Number(btn.dataset.idx) || 0;
        render();
      });
    });
    panel.querySelectorAll('[data-rel]').forEach((btn) => {
      btn.addEventListener('click', () => onRelationPick(btn.dataset.rel));
    });
  }

  return {
    showPending(literal) {
      model = null;
      readingIdx = 0;
      panel.hidden = false;
      panel.innerHTML = `
        <header class="entry-detail-panel__header">
          <h2 class="entry-detail-panel__title">${escapeHtml(tDetail('detail.title', lang))}</h2>
          <button type="button" class="entry-detail-panel__close" aria-label="${escapeHtml(tDetail('detail.close', lang))}">×</button>
        </header>
        <div class="entry-detail-panel__body">
          <div class="entry-detail-panel__hero">
            <div class="entry-detail-panel__literal">${escapeHtml(literal)}</div>
          </div>
          <p class="entry-detail-panel__loading">${escapeHtml(lang === 'en' ? 'Loading…' : '載入中…')}</p>
        </div>`;
      panel.querySelector('.entry-detail-panel__close')?.addEventListener('click', onClose);
    },
    setModel(next, preferredJyutping) {
      model = next;
      readingIdx = pickPreferredReadingIndex(model?.readings ?? [], preferredJyutping);
      render();
    },
    close() {
      model = null;
      panel.hidden = true;
      panel.innerHTML = '';
    },
    isOpen() {
      return Boolean(model);
    },
    resolveClick(payload, state) {
      return resolveListClickAction({
        panelOpen: state.panelOpen,
        activeLiteral: state.activeLiteral,
        targetLiteral: payload.literal,
        fromRelationChip: payload.fromRelationChip,
      });
    },
  };
}