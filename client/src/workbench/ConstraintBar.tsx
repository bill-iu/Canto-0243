import type { ReplacementPlanV1 } from './contracts.ts';
import {
  emptyPhonemeDimPicks,
  spanPositionOptions,
  type PhonemeDimPicks,
} from './replacement-span.ts';

interface Props {
  mode: ReplacementPlanV1['mode'];
  semanticIntent: ReplacementPlanV1['semanticIntent'];
  onModeChange: (mode: ReplacementPlanV1['mode']) => void;
  onSemanticChange: (intent: ReplacementPlanV1['semanticIntent']) => void;
  spanWidth: number;
  rhyme: PhonemeDimPicks;
  initial: PhonemeDimPicks;
  onRhymeChange: (next: PhonemeDimPicks) => void;
  onInitialChange: (next: PhonemeDimPicks) => void;
}

function toggleWhole(picks: PhonemeDimPicks, on: boolean): PhonemeDimPicks {
  return on ? { whole: true, head: false, tail: false, middles: [] } : emptyPhonemeDimPicks();
}

function toggleHead(picks: PhonemeDimPicks, on: boolean): PhonemeDimPicks {
  if (on) return { ...picks, whole: false, head: true };
  return { ...picks, head: false };
}

function toggleTail(picks: PhonemeDimPicks, on: boolean): PhonemeDimPicks {
  if (on) return { ...picks, whole: false, tail: true };
  return { ...picks, tail: false };
}

function toggleMiddle(picks: PhonemeDimPicks, offset: number, on: boolean): PhonemeDimPicks {
  const middles = new Set(picks.middles);
  if (on) middles.add(offset);
  else middles.delete(offset);
  return { whole: false, head: picks.head, tail: picks.tail, middles: [...middles].sort((a, b) => a - b) };
}

function DimChecklist({
  legend,
  wholeLabel,
  positionSuffix,
  width,
  picks,
  onChange,
}: {
  legend: string;
  wholeLabel: string;
  positionSuffix: string;
  width: number;
  picks: PhonemeDimPicks;
  onChange: (next: PhonemeDimPicks) => void;
}) {
  const positions = spanPositionOptions(width);
  const noneOn = !picks.whole && !picks.head && !picks.tail && picks.middles.length === 0;
  return (
    <fieldset className="phoneme-dim" disabled={width < 1}>
      <legend>{legend}</legend>
      <label className="phoneme-dim__option">
        <input type="checkbox" checked={noneOn} onChange={() => onChange(emptyPhonemeDimPicks())} />
        不限制
      </label>
      {positions.map((option) => {
        const isOn = width === 1
          ? picks.head
          : option.key === 'head'
            ? picks.head
            : option.key === 'tail'
              ? picks.tail
              : picks.middles.includes(option.key);
        return (
          <label key={String(option.key)} className="phoneme-dim__option">
            <input
              type="checkbox"
              checked={picks.whole ? false : isOn}
              disabled={picks.whole}
              onChange={(event) => {
                const on = event.target.checked;
                if (width === 1) {
                  onChange(on ? { whole: false, head: true, tail: false, middles: [] } : emptyPhonemeDimPicks());
                  return;
                }
                if (option.key === 'head') onChange(toggleHead(picks, on));
                else if (option.key === 'tail') onChange(toggleTail(picks, on));
                else onChange(toggleMiddle(picks, option.key, on));
              }}
            />
            {option.label}{positionSuffix}
          </label>
        );
      })}
      <label className="phoneme-dim__option">
        <input
          type="checkbox"
          checked={picks.whole}
          onChange={(event) => onChange(toggleWhole(picks, event.target.checked))}
        />
        {wholeLabel}
      </label>
    </fieldset>
  );
}

export function ConstraintBar({
  mode,
  semanticIntent,
  onModeChange,
  onSemanticChange,
  spanWidth,
  rhyme,
  initial,
  onRhymeChange,
  onInitialChange,
}: Props) {
  return (
    <section className="constraint-bar" aria-labelledby="constraintHeading">
      <h2 id="constraintHeading">本次替換條件</h2>
      <label>聲調精度
        <select value={mode} onChange={(event) => onModeChange(event.target.value as Props['mode'])}>
          <option value="m1">0243</option>
          <option value="m2">02493</option>
          <option value="m3">394052</option>
        </select>
      </label>
      <label>原意關係
        <select value={semanticIntent} onChange={(event) => onSemanticChange(event.target.value as Props['semanticIntent'])}>
          <option value="ranked">近義優先，保留其他選擇</option>
          <option value="direct_only">只看直接近義</option>
          <option value="off">不設語意條件</option>
        </select>
      </label>
      <div className="phoneme-dims" aria-label="讀音約束">
        <DimChecklist
          legend="同韻"
          wholeLabel="整段押韻"
          positionSuffix="同韻"
          width={spanWidth}
          picks={rhyme}
          onChange={onRhymeChange}
        />
        <DimChecklist
          legend="同聲"
          wholeLabel="整段同聲母"
          positionSuffix="同聲"
          width={spanWidth}
          picks={initial}
          onChange={onInitialChange}
        />
      </div>
      <p>更改條件只會重新找候選，不會改動句面。</p>
      <p className="shortcut-hint">捷徑：空白鍵鎖／解鎖 · U 復原 · 1–3 分組 · Enter 首候選 · A 套用</p>
    </section>
  );
}
