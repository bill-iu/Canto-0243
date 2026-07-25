import { useEffect, useRef } from 'react';

import { posDisplayChips } from '../pos/carrier.ts';
import type { LineDraft } from './line-draft.ts';
import type { WorkbenchCandidate } from './contracts.ts';
import { candidateReasonLabel } from './candidate-reason-i18n.ts';

interface Props {
  candidate: WorkbenchCandidate;
  draft: LineDraft;
  lang?: 'zh' | 'zh-Hans';
  onApply: () => void;
  onClose: () => void;
  onOpenInSearch: () => void;
}

export function ComparePanel({ candidate, draft, lang, onApply, onClose, onOpenInSearch }: Props) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const selection = draft.selection!;
  const preview = [
    ...draft.slots.slice(0, selection.start).map((slot) => slot.surface),
    candidate.literal,
    ...draft.slots.slice(selection.start + selection.width).map((slot) => slot.surface),
  ].join('');
  const relationSource = candidate.reasons.find((reason) => reason.source)?.source;
  const posChips = posDisplayChips(candidate.literal);
  useEffect(() => { headingRef.current?.focus(); }, []);
  return (
    <aside
      className="compare-panel"
      aria-labelledby="compareHeading"
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
        if (event.key === 'a' || event.key === 'A') {
          event.preventDefault();
          onApply();
        }
      }}
    >
      <button type="button" className="compare-close" onClick={onClose} aria-label="關閉比較">×</button>
      <p className="eyebrow">全句預覽</p>
      <h2 id="compareHeading" ref={headingRef} tabIndex={-1}>{candidate.literal}</h2>
      <p className="compare-preview">{preview}</p>
      <dl>
        <div><dt>粵拼</dt><dd>{candidate.jyutping}</dd></div>
        <div><dt>0243 碼</dt><dd>{candidate.code}</dd></div>
        <div><dt>排序順位</dt><dd>{candidate.sourceRank}</dd></div>
        {posChips.length ? (
          <div>
            <dt>詞性</dt>
            <dd className="compare-pos-chips">
              {posChips.map((chip) => (
                <span key={chip} className="compare-pos-chip">{chip}</span>
              ))}
            </dd>
          </div>
        ) : null}
        {relationSource ? <div><dt>關係來源</dt><dd>{relationSource}</dd></div> : null}
      </dl>
      <h3>為何出現</h3>
      <ul>{candidate.reasons.map((reason, index) => <li key={`${reason.kind}-${index}`}>{candidateReasonLabel(reason.kind, lang)}</li>)}</ul>
      <button type="button" className="primary-action" onClick={onApply}>套用這個選擇</button>
      <button type="button" className="secondary-action" onClick={onOpenInSearch}>在搜尋頁查看</button>
      <p className="compare-note">只有按下「套用」才會改動句面。</p>
    </aside>
  );
}
