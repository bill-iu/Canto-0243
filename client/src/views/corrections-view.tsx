/**
 * Portable maintainer: 詞庫勘誤 — mirrors shared/lexicon-corrections.mjs main path.
 */
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getCorrectionsCopy } from '../../../shared/corrections-i18n.mjs';

interface WordRow {
  char: string;
  code: string;
  jyutping: string;
}

interface SessionRow extends WordRow {
  action: string;
  value: string;
  note: string;
}

export interface CorrectionsViewProps {
  lang?: 'zh' | 'zh-Hans' | 'en';
  prefetchChar?: string;
}

function apiDetail(body: { detail?: unknown }, fallback: string): string {
  const d = body.detail;
  if (typeof d === 'string' && d.trim()) return d;
  return fallback;
}

export function CorrectionsView({ lang = 'zh', prefetchChar = '' }: CorrectionsViewProps) {
  const copy = getCorrectionsCopy(lang);
  const [char, setChar] = useState(prefetchChar);
  const [rows, setRows] = useState<WordRow[]>([]);
  const [selected, setSelected] = useState<WordRow | null>(null);
  const [newJyutping, setNewJyutping] = useState('');
  const [note, setNote] = useState('');
  const [previewCode, setPreviewCode] = useState('');
  const [sessionRows, setSessionRows] = useState<SessionRow[]>([]);
  const [ok, setOk] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [statsHtml, setStatsHtml] = useState<string | null>(null);
  const charRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    charRef.current?.focus({ preventScroll: true });
    void (async () => {
      try {
        const res = await fetch('/words/db-stats/', { cache: 'no-store' });
        if (!res.ok) throw new Error(String(res.status));
        const { wordCount, tableCount } = (await res.json()) as {
          wordCount: number;
          tableCount: number;
        };
        setStatsHtml(copy.stats(Number(wordCount), Number(tableCount)));
      } catch {
        setStatsHtml(copy.statsFailed);
      }
    })();
  }, [lang]);

  useEffect(() => {
    const prefetch = prefetchChar.trim();
    if (!prefetch) return;
    setChar(prefetch);
    void (async () => {
      setBusy(true);
      setOk(null);
      setErr(null);
      try {
        const res = await fetch(`/words/rows?char=${encodeURIComponent(prefetch)}`);
        if (!res.ok) throw new Error('lookup failed');
        const next = (await res.json()) as WordRow[];
        setRows(next);
        if (!next.length) {
          setErr(copy.notFound);
          return;
        }
        if (next.length === 1) {
          const row = next[0];
          setSelected(row);
          setNewJyutping(row.jyutping || '');
          setNote('');
          try {
            const previewRes = await fetch(
              `/lexicon/code-preview?jyutping=${encodeURIComponent(row.jyutping || '')}`,
            );
            if (previewRes.ok) {
              const body = (await previewRes.json()) as { code?: string };
              setPreviewCode(body.code || '');
            }
          } catch {
            setPreviewCode('');
          }
        }
      } catch {
        setRows([]);
        setErr(copy.cannotReach);
      } finally {
        setBusy(false);
      }
    })();
    // ponytail: refresh the debug→corrections deep-link prefetch when its inputs change
  }, [lang, prefetchChar]);

  const clearSelection = () => {
    setSelected(null);
    setPreviewCode('');
    setNewJyutping('');
  };

  const refreshCodePreview = async (jyutping: string, row: WordRow | null) => {
    const literal = jyutping.trim();
    if (!literal || !row) {
      setPreviewCode('');
      return;
    }
    try {
      const res = await fetch(`/lexicon/code-preview?jyutping=${encodeURIComponent(literal)}`);
      if (!res.ok) throw new Error('preview failed');
      const body = (await res.json()) as { code?: string };
      setPreviewCode(body.code || '');
    } catch {
      setPreviewCode('');
    }
  };

  const selectRow = (row: WordRow) => {
    setSelected(row);
    setNewJyutping(row.jyutping || '');
    setNote('');
    setOk(null);
    setErr(null);
    void refreshCodePreview(row.jyutping, row);
  };

  const lookupRows = async (literalIn?: string) => {
    const literal = (literalIn ?? char).trim();
    if (!literal) {
      setErr(copy.enterLiteral);
      return;
    }
    setBusy(true);
    setOk(null);
    setErr(null);
    clearSelection();
    try {
      const res = await fetch(`/words/rows?char=${encodeURIComponent(literal)}`);
      if (!res.ok) throw new Error('lookup failed');
      const next = (await res.json()) as WordRow[];
      setRows(next);
      if (!next.length) {
        setErr(copy.notFound);
        return;
      }
      if (next.length === 1) selectRow(next[0]);
    } catch {
      setRows([]);
      setErr(copy.cannotReach);
    } finally {
      setBusy(false);
    }
  };

  const submitCorrection = async (action: string, value: string) => {
    if (!selected) {
      setErr(copy.selectRow);
      return;
    }
    setBusy(true);
    setOk(null);
    setErr(null);
    try {
      const res = await fetch('/lexicon/corrections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          char: selected.char,
          code: selected.code,
          jyutping: selected.jyutping,
          action,
          value,
          note: note.trim(),
        }),
      });
      const body = (await res.json().catch(() => ({}))) as {
        detail?: unknown;
        message?: string;
        char?: string;
        code?: string;
        jyutping?: string;
        action?: string;
        value?: string;
        note?: string;
      };
      if (!res.ok) {
        setErr(apiDetail(body, copy.submitFailed));
        return;
      }
      setSessionRows((prev) => [
        {
          char: body.char || selected.char,
          code: body.code || selected.code,
          jyutping: body.jyutping || selected.jyutping,
          action: body.action || action,
          value: body.value || value,
          note: body.note || '',
        },
        ...prev,
      ]);
      setOk(
        `${body.message || copy.queued} ${copy.updateAfterApply}`,
      );
    } catch {
      setErr(copy.cannotReach);
    } finally {
      setBusy(false);
    }
  };

  const onLookup = (event: FormEvent) => {
    event.preventDefault();
    void lookupRows();
  };

  const onSetJyutping = async () => {
    const next = newJyutping.trim();
    if (!next) {
      setErr(copy.enterNewJyutping);
      return;
    }
    if (selected && next === selected.jyutping) {
      setErr(copy.sameJyutping);
      return;
    }
    await submitCorrection('set_jyutping', next);
  };

  const onRecalcCode = async () => {
    if (!selected) return;
    await refreshCodePreview(selected.jyutping, selected);
    // refreshCodePreview is async state — re-fetch for decision
    try {
      const res = await fetch(
        `/lexicon/code-preview?jyutping=${encodeURIComponent(selected.jyutping)}`,
      );
      if (!res.ok) throw new Error('preview failed');
      const body = (await res.json()) as { code?: string };
      const code = body.code || '';
      setPreviewCode(code);
      if (!code) {
        setErr(copy.computeFailed);
        return;
      }
      if (code === selected.code) {
        setErr(copy.codeMatches);
        return;
      }
      await submitCorrection('set_code', code);
    } catch {
      setErr(copy.computeFailed);
    }
  };

  const showPreview =
    Boolean(previewCode) && Boolean(selected) && previewCode !== selected?.code;

  return (
    <section
      className="relation-view relation-main corrections-view"
      aria-labelledby="correctionsTitle"
    >
      <header className="relation-hero">
        <h1 id="correctionsTitle">{copy.title}</h1>
        <p className="relation-lede">
          {copy.ledeBeforeCode}<code translate="no">debug</code>{copy.ledeAfterCode}
        </p>
        {statsHtml ? (
          <div className="db-stats" aria-live="polite">
            <p>{statsHtml}</p>
          </div>
        ) : null}
      </header>

      <form className="relation-form" onSubmit={onLookup}>
        <div className="field">
          <label htmlFor="correctionChar">{copy.literal}</label>
          <span className="hint">
            {copy.literalHint}
          </span>
          <div className="search-input-wrap" data-input-wrap="">
            <input
              ref={charRef}
              type="text"
              id="correctionChar"
              name="char"
              required
              autoComplete="off"
              spellCheck={false}
              value={char}
              onChange={(e) => setChar(e.target.value)}
            />
          </div>
        </div>
        <div className="actions">
          <button className="primary-button" type="submit" disabled={busy}>
            {copy.lookupRows}
          </button>
        </div>
      </form>

      {rows.length > 0 ? (
        <div className="corrections-rows">
          <p className="hint" id="correctionRowsHint">
            {copy.selectRowHint}
          </p>
          <div
            className="corrections-row-list"
            role="radiogroup"
            aria-labelledby="correctionRowsHint"
          >
            {rows.map((row, index) => {
              const id = `correction-row-${index}`;
              return (
                <label key={`${row.code}-${row.jyutping}`} className="corrections-row-choice" htmlFor={id}>
                  <input
                    type="radio"
                    name="correction_row"
                    id={id}
                    checked={
                      selected?.code === row.code && selected?.jyutping === row.jyutping
                    }
                    onChange={() => selectRow(row)}
                  />
                  <span>
                    code {row.code} · {row.jyutping}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      ) : null}

      {selected ? (
        <form className="relation-form" onSubmit={(e) => e.preventDefault()}>
          <div className="field">
            <label htmlFor="correctionNewJyutping">{copy.newJyutping}</label>
            <span className="hint">
              {copy.newJyutpingHint}
            </span>
            <div className="search-input-wrap" data-input-wrap="">
              <input
                type="text"
                id="correctionNewJyutping"
                name="new_jyutping"
                autoComplete="off"
                spellCheck={false}
                value={newJyutping}
                onChange={(e) => {
                  setNewJyutping(e.target.value);
                  void refreshCodePreview(e.target.value, selected);
                }}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="correctionNote">{copy.note}</label>
            <span className="hint">
              {copy.noteHint}
            </span>
            <div className="search-input-wrap" data-input-wrap="">
              <input
                type="text"
                id="correctionNote"
                name="note"
                autoComplete="off"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>
          </div>
          {showPreview ? (
            <div className="field">
              <p className="corrections-preview">
                {copy.preview(previewCode, selected.code)}
              </p>
            </div>
          ) : null}
          <div className="actions">
            <button
              className="primary-button"
              type="button"
              disabled={busy}
              onClick={() => void onSetJyutping()}
            >
              {copy.setJyutping}
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={busy}
              onClick={() => void onRecalcCode()}
            >
              {copy.recalcCode}
            </button>
          </div>
          {ok ? (
            <div className="status ok" role="status">
              {ok}
            </div>
          ) : null}
          {err ? (
            <div className="status err" role="alert">
              {err}
            </div>
          ) : null}
        </form>
      ) : err && !rows.length ? (
        <div className="status err" role="alert">
          {err}
        </div>
      ) : null}

      {sessionRows.length > 0 ? (
        <section className="corrections-session" aria-labelledby="correctionSessionTitle">
          <h2 className="corrections-session__title" id="correctionSessionTitle">
            {copy.session}
          </h2>
          <ul className="corrections-session__list">
            {sessionRows.map((row, i) => (
              <li key={`${row.char}-${row.code}-${row.action}-${i}`}>
                {row.char} · code {row.code} · {row.jyutping} → {row.action} {row.value}
                {row.note ? `（${row.note}）` : ''}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
