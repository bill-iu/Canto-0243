import type { ReplacementPlanV1 } from './contracts.ts';

interface Props {
  mode: ReplacementPlanV1['mode'];
  semanticIntent: ReplacementPlanV1['semanticIntent'];
  onModeChange: (mode: ReplacementPlanV1['mode']) => void;
  onSemanticChange: (intent: ReplacementPlanV1['semanticIntent']) => void;
  anchorsDisabled: boolean;
  onAddFinalAnchor: () => void;
  onAddInitialAnchor: () => void;
}

export function ConstraintBar({ mode, semanticIntent, onModeChange, onSemanticChange, anchorsDisabled, onAddFinalAnchor, onAddInitialAnchor }: Props) {
  return (
    <section className="constraint-bar" aria-labelledby="constraintHeading">
      <h2 id="constraintHeading">本次替換條件</h2>
      <label>聲調精度
        <select value={mode} onChange={(event) => onModeChange(event.target.value as Props['mode'])}>
          <option value="m3">六聲（精確）</option>
          <option value="m2">緊</option>
          <option value="m1">鬆</option>
        </select>
      </label>
      <label>原意關係
        <select value={semanticIntent} onChange={(event) => onSemanticChange(event.target.value as Props['semanticIntent'])}>
          <option value="ranked">近義優先，保留其他選擇</option>
          <option value="direct_only">只看直接近義</option>
          <option value="off">不設語意條件</option>
        </select>
      </label>
      <div className="anchor-actions" aria-label="讀音錨點">
        <button type="button" disabled={anchorsDisabled} onClick={onAddFinalAnchor}>末格同韻</button>
        <button type="button" disabled={anchorsDisabled} onClick={onAddInitialAnchor}>首格同聲</button>
      </div>
      <p>更改條件只會重新找候選，不會改動句面。</p>
      <p className="shortcut-hint">捷徑：L 鎖選段 · U 復原 · 1–3 分組 · Enter 首候選 · A 套用</p>
    </section>
  );
}
