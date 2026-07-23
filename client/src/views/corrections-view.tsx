/**
 * Portable maintainer: 詞庫勘誤 — mirrors shared/lexicon-corrections.mjs main path.
 */
import { useEffect, useRef, useState, type FormEvent } from 'react';

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
  lang?: 'zh' | 'en';
  prefetchChar?: string;
}

function apiDetail(body: { detail?: unknown }, fallback: string): string {
  const d = body.detail;
  if (typeof d === 'string' && d.trim()) return d;
  return fallback;
}

export function CorrectionsView({ lang = 'zh', prefetchChar = '' }: CorrectionsViewProps) {
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
        setStatsHtml(
          lang === 'en'
            ? `Entries: ${Number(wordCount).toLocaleString()} · Tables: ${Number(tableCount).toLocaleString()}`
            : `詞條數量: ${Number(wordCount).toLocaleString()} · 資料表數量: ${Number(tableCount).toLocaleString()}`,
        );
      } catch {
        setStatsHtml(lang === 'en' ? 'Could not load DB stats' : '無法載入資料庫統計');
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
          setErr(lang === 'en' ? 'Literal not found in lexicon.' : '詞庫中找不到此字面。');
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
        setErr(
          lang === 'en' ? 'Cannot reach the server. Is it running?' : '無法連線後端。請確認伺服器已啟動。',
        );
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
      setErr(lang === 'en' ? 'Enter a literal.' : '請輸入字面。');
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
        setErr(lang === 'en' ? 'Literal not found in lexicon.' : '詞庫中找不到此字面。');
        return;
      }
      if (next.length === 1) selectRow(next[0]);
    } catch {
      setRows([]);
      setErr(lang === 'en' ? 'Cannot reach the server. Is it running?' : '無法連線後端。請確認伺服器已啟動。');
    } finally {
      setBusy(false);
    }
  };

  const submitCorrection = async (action: string, value: string) => {
    if (!selected) {
      setErr(lang === 'en' ? 'Select a lexicon row first.' : '請先選取收錄列。');
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
        setErr(apiDetail(body, lang === 'en' ? 'Submit failed.' : '提交失敗。'));
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
        `${body.message || (lang === 'en' ? 'Queued.' : '已入隊。')} ${
          lang === 'en' ? 'Search results update after apply.' : '搜尋結果待套用後更新。'
        }`,
      );
    } catch {
      setErr(lang === 'en' ? 'Cannot reach the server. Is it running?' : '無法連線後端。請確認伺服器已啟動。');
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
      setErr(lang === 'en' ? 'Enter new Jyutping.' : '請填寫新粵拼。');
      return;
    }
    if (selected && next === selected.jyutping) {
      setErr(lang === 'en' ? 'New Jyutping matches current.' : '新粵拼與現有相同。');
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
        setErr(lang === 'en' ? 'Could not compute code.' : '無法計算 code。');
        return;
      }
      if (code === selected.code) {
        setErr(lang === 'en' ? 'Code already matches Jyutping.' : 'code 與粵拼已一致，無需重算。');
        return;
      }
      await submitCorrection('set_code', code);
    } catch {
      setErr(lang === 'en' ? 'Could not compute code.' : '無法計算 code。');
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
        <h1 id="correctionsTitle">{lang === 'en' ? 'Lexicon corrections' : '詞庫勘誤'}</h1>
        <p className="relation-lede">
          {lang === 'en' ? (
            <>
              Maintainer only: type <code translate="no">debug</code> in search to open this tab.
              Queue Jyutping / 0243 fixes to pending; search updates after batch apply.
            </>
          ) : (
            <>
              維護者專用：在搜尋框輸入 <code translate="no">debug</code> 開此分頁。記錄標音或 0243
              碼問題至 pending 隊列；搜尋結果待批次套用後才更新。
            </>
          )}
        </p>
        {statsHtml ? (
          <div className="db-stats" aria-live="polite">
            <p>{statsHtml}</p>
          </div>
        ) : null}
      </header>

      <form className="relation-form" onSubmit={onLookup}>
        <div className="field">
          <label htmlFor="correctionChar">{lang === 'en' ? 'Literal' : '字面'}</label>
          <span className="hint">
            {lang === 'en'
              ? 'Look up lexicon rows for this literal, then pick one to fix'
              : '輸入已收錄詞條字面，列出所有收錄列後選取要修正的一列'}
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
            {lang === 'en' ? 'Look up rows' : '查收錄列'}
          </button>
        </div>
      </form>

      {rows.length > 0 ? (
        <div className="corrections-rows">
          <p className="hint" id="correctionRowsHint">
            {lang === 'en' ? 'Select the row to correct:' : '選取要修正的收錄列：'}
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
            <label htmlFor="correctionNewJyutping">{lang === 'en' ? 'New Jyutping' : '新粵拼'}</label>
            <span className="hint">
              {lang === 'en'
                ? 'Fill when changing Jyutping; leave as-is for code recalc'
                : '改粵拼時填寫；重算 code 可留空'}
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
            <label htmlFor="correctionNote">{lang === 'en' ? 'Note' : '備註'}</label>
            <span className="hint">
              {lang === 'en' ? 'Optional: reason or reference' : '可選：發現原因或參考'}
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
                {lang === 'en'
                  ? `Jyutping maps to code ${previewCode} (current ${selected.code})`
                  : `依粵拼應為 code ${previewCode}（現有 ${selected.code}）`}
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
              {lang === 'en' ? 'Set Jyutping' : '改粵拼'}
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={busy}
              onClick={() => void onRecalcCode()}
            >
              {lang === 'en' ? 'Recalc code' : '重算 code'}
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
            {lang === 'en' ? 'This session' : '本次 session'}
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
