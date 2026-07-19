import type { LineDraft } from './line-draft.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';

interface Props {
  draft: LineDraft;
  readings: PwaLineReadingSlot[];
  onToggleLock: (pos: number) => void;
  onChooseReading: (pos: number, jyutping: string, code: string) => void;
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

export function SentenceCanvas({ draft, readings, onToggleLock, onChooseReading }: Props) {
  const summary = codeSummary(draft);
  const span = draft.selection;
  const inSpan = (pos: number) => Boolean(
    span && pos >= span.start && pos < span.start + span.width,
  );
  const move = (pos: number, delta: number) => {
    const next = Math.max(0, Math.min(draft.slots.length - 1, pos + delta));
    document.querySelector<HTMLButtonElement>(`[data-line-slot="${next}"]`)?.focus();
  };

  return (
    <section className="sentence-canvas" aria-labelledby="sentenceHeading">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">逐字句格</p>
          <h2 id="sentenceHeading">點擊標定替換段；再點取消</h2>
        </div>
        {draft.undo ? <span className="quiet-status">最近一次操作可復原</span> : null}
      </div>
      {summary ? <p className="code-summary" aria-label="完整碼摘要">{summary}</p> : null}
      <div className="line-slots" role="list" aria-label="歌詞字位">
        {draft.slots.map((slot, pos) => {
          const reading = readings[pos];
          const locked = slot.locked;
          const spanned = inSpan(pos);
          const codeAsSurface = !slot.surface && Boolean(slot.code);
          const unresolved = reading?.kind === 'unresolved';
          const staticJyutping = !reading?.needsChoice
            ? (slot.reading || reading?.choices[0]?.jyutping || '')
            : '';
          const ariaReading = unresolved
            ? '讀音未收錄'
            : (slot.reading || reading?.choices[0]?.jyutping || (codeAsSurface ? '碼格' : '讀音未定'));

          return (
            <div className="line-slot-wrap" role="listitem" key={pos}>
              <button
                type="button"
                className={`line-slot${locked ? ' is-locked' : ''}${spanned && !locked ? ' is-in-span' : ''}${unresolved ? ' has-unread' : ''}`}
                data-line-slot={pos}
                aria-pressed={locked}
                aria-label={`第 ${pos + 1} 個字，${slot.surface || (codeAsSurface ? `碼 ${slot.code}` : '空白')}，${ariaReading}，${slot.code || '未有碼'}，${locked ? '已標定' : '未標定'}${spanned && !locked ? '，在替換段內' : ''}`}
                onClick={() => onToggleLock(pos)}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                    event.preventDefault();
                    move(pos, event.key === 'ArrowLeft' ? -1 : 1);
                  } else if (event.key === ' ') {
                    event.preventDefault();
                    onToggleLock(pos);
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
