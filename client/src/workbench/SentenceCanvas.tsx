import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';

import type { LineDraft } from './line-draft.ts';
import { parseManualCell, parseSpanManual } from './manual-slot-input.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';

interface Props {
  draft: LineDraft;
  readings: PwaLineReadingSlot[];
  onToggleLock: (pos: number) => void;
  onChooseReading: (pos: number, jyutping: string, code: string) => void;
  onSetSlotManual: (pos: number, surface: string, code?: string) => void;
  onClearSurfaces: () => void;
  onApplySpanInput: (parsed: ReturnType<typeof parseSpanManual> & { ok: true }) => void;
  onSpanInputError: (message: string) => void;
  spanInputError?: string;
}

function codeSummary(draft: LineDraft): string | null {
  if (!draft.slots.length || draft.slots.some((slot) => slot.surface)) return null;
  if (!draft.slots.every((slot) => slot.code)) return null;
  return draft.slots.map((slot) => slot.code).join('');
}

function surfaceLabel(slot: LineDraft['slots'][number]): string {
  if (slot.surface) return slot.surface;
  if (slot.code) return slot.code;
  return '＿';
}

const CLICK_DELAY_MS = 280;

export function SentenceCanvas({
  draft,
  readings,
  onToggleLock,
  onChooseReading,
  onSetSlotManual,
  onClearSurfaces,
  onApplySpanInput,
  onSpanInputError,
  spanInputError,
}: Props) {
  const summary = codeSummary(draft);
  const span = draft.selection;
  const [editingPos, setEditingPos] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [spanRaw, setSpanRaw] = useState('');
  const [spanPanelOpen, setSpanPanelOpen] = useState(false);
  const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const editInputRef = useRef<HTMLInputElement | null>(null);
  const spanInputRef = useRef<HTMLInputElement | null>(null);
  const editingPosRef = useRef<number | null>(null);
  const editValueRef = useRef('');
  editingPosRef.current = editingPos;
  editValueRef.current = editValue;

  useEffect(() => {
    setSpanRaw('');
    if (!span) setSpanPanelOpen(false);
  }, [span?.start, span?.width, span]);

  useEffect(() => {
    if (editingPos == null) return;
    editInputRef.current?.focus();
    editInputRef.current?.select();
  }, [editingPos]);

  useEffect(() => {
    if (!spanPanelOpen || !span) return;
    spanInputRef.current?.focus();
  }, [spanPanelOpen, span]);

  const inSpan = (pos: number) => Boolean(
    span && pos >= span.start && pos < span.start + span.width,
  );
  const move = (pos: number, delta: number) => {
    const next = Math.max(0, Math.min(draft.slots.length - 1, pos + delta));
    document.querySelector<HTMLButtonElement>(`[data-line-slot="${next}"]`)?.focus();
  };

  const clearClickTimer = () => {
    if (!clickTimer.current) return;
    clearTimeout(clickTimer.current);
    clickTimer.current = null;
  };

  const beginEdit = (pos: number) => {
    clearClickTimer();
    const slot = draft.slots[pos];
    if (!slot) return;
    setEditingPos(pos);
    setEditValue(slot.surface || slot.code || '');
  };

  const cancelEdit = () => {
    editingPosRef.current = null;
    setEditingPos(null);
    setEditValue('');
  };

  const confirmEdit = () => {
    const pos = editingPosRef.current;
    if (pos == null) return;
    editingPosRef.current = null;
    const parsed = parseManualCell(editValueRef.current);
    setEditingPos(null);
    setEditValue('');
    if (!parsed.ok) return;
    onSetSlotManual(pos, parsed.surface, parsed.code);
  };

  const scheduleToggle = (pos: number) => {
    clearClickTimer();
    clickTimer.current = setTimeout(() => {
      clickTimer.current = null;
      onToggleLock(pos);
    }, CLICK_DELAY_MS);
  };

  const submitSpan = (event: FormEvent) => {
    event.preventDefault();
    if (!span) return;
    const parsed = parseSpanManual(spanRaw, span.width);
    if (!parsed.ok) {
      onSpanInputError(
        parsed.error === 'width'
          ? `長度須為 ${span.width} 格。`
          : '請輸入字面、碼、通配、混合或平仄，長度須等於鎖定段。',
      );
      return;
    }
    onSpanInputError('');
    onApplySpanInput(parsed);
    setSpanRaw('');
    setSpanPanelOpen(false);
  };

  return (
    <section className="sentence-canvas" aria-labelledby="sentenceHeading">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">逐字句格</p>
          <h2 id="sentenceHeading">點擊鎖定，雙擊改字</h2>
        </div>
        <div className="sentence-canvas__heading-actions">
          {draft.undo ? <span className="quiet-status">最近一次操作可復原</span> : null}
          <button
            type="button"
            className="canvas-clear-surfaces"
            title="清空句格（恢復空白）"
            aria-label="清空句格"
            onClick={() => { cancelEdit(); setSpanPanelOpen(false); onClearSurfaces(); }}
          >清空</button>
          <button
            type="button"
            className={`span-hand-toggle${spanPanelOpen ? ' is-open' : ''}`}
            disabled={!span}
            aria-expanded={spanPanelOpen}
            aria-controls="spanHandPanel"
            title={span ? '手打替換段' : '請先鎖定替換段'}
            aria-label={span ? '手打替換段' : '手打替換段（請先鎖定）'}
            onClick={() => {
              if (!span) return;
              setSpanPanelOpen((open) => !open);
              onSpanInputError('');
            }}
          >
            ✎
          </button>
        </div>
      </div>
      {summary ? <p className="code-summary" aria-label="完整碼摘要">{summary}</p> : null}
      {span && spanPanelOpen ? (
        <form id="spanHandPanel" className="span-hand-input" onSubmit={submitSpan}>
          <label htmlFor="spanHandInput">
            手打替換段（{span.width} 格；規則同起句）
            <input
              id="spanHandInput"
              ref={spanInputRef}
              value={spanRaw}
              onChange={(event) => setSpanRaw(event.target.value)}
              maxLength={span.width}
              spellCheck={false}
              placeholder={span.width === 1 ? '一字或一碼' : `輸入 ${span.width} 格`}
              aria-invalid={Boolean(spanInputError)}
              aria-describedby={spanInputError ? 'spanHandHint' : undefined}
            />
          </label>
          <button type="submit">套用</button>
          <button type="button" className="span-hand-input__cancel" onClick={() => {
            setSpanPanelOpen(false);
            setSpanRaw('');
            onSpanInputError('');
          }}>收起</button>
          {spanInputError ? <p id="spanHandHint" className="span-hand-input__error">{spanInputError}</p> : null}
        </form>
      ) : null}
      <div className="line-slots" role="list" aria-label="歌詞字位">
        {draft.slots.map((slot, pos) => {
          const reading = readings[pos];
          const locked = slot.locked;
          const spanned = inSpan(pos);
          const codeAsSurface = !slot.surface && Boolean(slot.code);
          const unresolved = reading?.kind === 'unresolved';
          const editing = editingPos === pos;
          const staticJyutping = !reading?.needsChoice
            ? (slot.reading || reading?.choices[0]?.jyutping || '')
            : '';
          const ariaReading = unresolved
            ? '讀音未收錄'
            : (slot.reading || reading?.choices[0]?.jyutping || (codeAsSurface ? '碼格' : '讀音未定'));

          return (
            <div className="line-slot-wrap" role="listitem" key={pos}>
              {editing ? (
                <input
                  ref={editInputRef}
                  className="line-slot-edit"
                  value={editValue}
                  maxLength={1}
                  spellCheck={false}
                  aria-label={`編輯第 ${pos + 1} 個字`}
                  onChange={(event) => setEditValue(event.target.value)}
                  onBlur={confirmEdit}
                  onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      confirmEdit();
                    } else if (event.key === 'Escape') {
                      event.preventDefault();
                      cancelEdit();
                    }
                  }}
                />
              ) : (
                <button
                  type="button"
                  className={`line-slot${locked ? ' is-locked' : ''}${spanned && !locked ? ' is-in-span' : ''}${unresolved ? ' has-unread' : ''}`}
                  data-line-slot={pos}
                  aria-pressed={locked}
                  aria-label={`第 ${pos + 1} 個字，${slot.surface || (codeAsSurface ? `碼 ${slot.code}` : '空白')}，${ariaReading}，${slot.code || '未有碼'}，${locked ? '已鎖定' : '未鎖定'}${spanned && !locked ? '，在替換段內' : ''}`}
                  onClick={() => scheduleToggle(pos)}
                  onDoubleClick={() => beginEdit(pos)}
                  onKeyDown={(event) => {
                    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                      event.preventDefault();
                      move(pos, event.key === 'ArrowLeft' ? -1 : 1);
                    } else if (event.key === ' ') {
                      event.preventDefault();
                      onToggleLock(pos);
                    } else if (event.key === 'Enter' || event.key === 'F2') {
                      event.preventDefault();
                      beginEdit(pos);
                    }
                  }}
                >
                  <span className={`line-slot__surface${codeAsSurface ? ' is-code-surface' : ''}`}>
                    {surfaceLabel(slot)}
                  </span>
                  <span className="line-slot__code">{codeAsSurface ? '·' : (slot.code || '·')}</span>
                  {unresolved ? <span className="line-slot__warn" title="讀音未收錄" aria-hidden="true">!</span> : null}
                  <span className="line-slot__lock" aria-hidden="true">{locked ? '鎖' : ''}</span>
                </button>
              )}
              <div className="slot-reading-footer">
                {reading?.needsChoice ? (
                  <select
                    className="reading-choice"
                    aria-label={`第 ${pos + 1} 個字讀音`}
                    value={slot.reading || reading.choices[0]?.jyutping || ''}
                    title={slot.reading || reading.choices[0]?.jyutping || undefined}
                    onChange={(event) => {
                      const choice = reading.choices.find((item) => item.jyutping === event.target.value);
                      if (choice) onChooseReading(pos, choice.jyutping, choice.code);
                    }}
                  >
                    {reading.choices.map((choice) => (
                      <option key={choice.jyutping} value={choice.jyutping}>{choice.jyutping}</option>
                    ))}
                  </select>
                ) : staticJyutping ? (
                  <span className="reading-static" title={staticJyutping}>{staticJyutping}</span>
                ) : (
                  <span className="reading-footer-spacer" aria-hidden="true" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
