import type { LineDraft } from './line-draft.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';

interface Props {
  draft: LineDraft;
  readings: PwaLineReadingSlot[];
  onSelect: (start: number, width: number) => void;
  onToggleLock: (pos: number) => void;
  onChooseReading: (pos: number, jyutping: string, code: string) => void;
}

function codeSummary(draft: LineDraft): string | null {
  if (!draft.slots.length || draft.slots.some((slot) => slot.surface)) return null;
  if (!draft.slots.every((slot) => slot.code)) return null;
  return draft.slots.map((slot) => slot.code).join('');
}

export function SentenceCanvas({ draft, readings, onSelect, onToggleLock, onChooseReading }: Props) {
  const summary = codeSummary(draft);
  const selected = (pos: number) => Boolean(
    draft.selection && pos >= draft.selection.start && pos < draft.selection.start + draft.selection.width,
  );
  const extendTo = (pos: number) => {
    if (!draft.selection) {
      onSelect(pos, 1);
      return;
    }
    const start = Math.min(draft.selection.start, pos);
    const end = Math.max(draft.selection.start + draft.selection.width - 1, pos);
    if (end - start + 1 <= 4) onSelect(start, end - start + 1);
  };
  const move = (pos: number, delta: number, extend: boolean) => {
    const next = Math.max(0, Math.min(draft.slots.length - 1, pos + delta));
    if (!extend || !draft.selection) onSelect(next, 1);
    else extendTo(next);
    document.querySelector<HTMLButtonElement>(`[data-line-slot="${next}"]`)?.focus();
  };

  return (
    <section className="sentence-canvas" aria-labelledby="sentenceHeading">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">逐字句格</p>
          <h2 id="sentenceHeading">圈選一至四個相鄰字位</h2>
        </div>
        {draft.undo ? <span className="quiet-status">最近一次操作可復原</span> : null}
      </div>
      {summary ? <p className="code-summary" aria-label="完整碼摘要">{summary}</p> : null}
      <div className="line-slots" role="list" aria-label="歌詞字位">
        {draft.slots.map((slot, pos) => {
          const reading = readings[pos];
          const active = selected(pos);
          return (
            <div className="line-slot-wrap" role="listitem" key={pos}>
              <button
                type="button"
                className={`line-slot${active ? ' is-selected' : ''}${slot.locked ? ' is-locked' : ''}`}
                data-line-slot={pos}
                aria-pressed={active}
                aria-label={`第 ${pos + 1} 個字，${slot.surface || '空白'}，${slot.reading || '讀音未定'}，${slot.code || '未有碼'}，${slot.locked ? '已鎖定' : '未鎖定'}${active ? '，已選中' : ''}`}
                onClick={(event) => {
                  if (event.shiftKey) extendTo(pos);
                  else onSelect(pos, 1);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                    event.preventDefault();
                    move(pos, event.key === 'ArrowLeft' ? -1 : 1, event.shiftKey);
                  } else if (event.key === ' ') {
                    event.preventDefault();
                    onToggleLock(pos);
                  }
                }}
              >
                <span className="line-slot__surface">{slot.surface || '＿'}</span>
                <span className="line-slot__code">{slot.code || '·'}</span>
                <span className="line-slot__lock" aria-hidden="true">{slot.locked ? '鎖' : ''}</span>
              </button>
              {reading?.needsChoice ? (
                <select
                  className="reading-choice"
                  aria-label={`第 ${pos + 1} 個字讀音`}
                  value={slot.reading ?? ''}
                  onChange={(event) => {
                    const choice = reading.choices.find((item) => item.jyutping === event.target.value);
                    if (choice) onChooseReading(pos, choice.jyutping, choice.code);
                  }}
                >
                  {reading.choices.map((choice) => <option key={choice.jyutping} value={choice.jyutping}>{choice.jyutping}</option>)}
                </select>
              ) : reading?.kind === 'unresolved' ? <span className="slot-warning">讀音未收錄</span> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
