import { memo, useState } from 'react';

import type { CandidateGroup, CandidateGroups, WorkbenchCandidate } from './contracts.ts';
import { emptyPoolTip } from './limits.ts';
import { compactEntryLength } from '../compact-entry.ts';

const GROUPS: Array<[CandidateGroup, string]> = [
  ['direct_syn', '直接近義'],
  ['semantic_related', '語意相關'],
  ['sound_only', '只合音格'],
];
const COLLAPSIBLE_EMPTY_GROUPS: ReadonlySet<CandidateGroup> = new Set(['direct_syn', 'semantic_related']);

interface Props {
  groups: CandidateGroups;
  total: number;
  loadedCount: number;
  hasMore: boolean;
  loadingMore?: boolean;
  posFilterActive?: boolean;
  /** 替換段寬；空池輕提示用（ADR-0069） */
  spanWidth?: number;
  relaxed?: { kind: string; from?: string; to?: string } | null;
  semanticGap?: boolean;
  onPreview: (candidate: WorkbenchCandidate, origin: HTMLButtonElement) => void;
  onLoadMore?: () => void;
}

export const CandidateGrid = memo(function CandidateGrid({
  groups,
  total,
  loadedCount,
  hasMore,
  loadingMore,
  posFilterActive,
  spanWidth = 0,
  relaxed,
  semanticGap,
  onPreview,
  onLoadMore,
}: Props) {
  const status = posFilterActive
    ? `篩後 ${loadedCount}／池內 ${total}`
    : `已載 ${loadedCount}／池內 ${total}`;
  const poolTip = emptyPoolTip(spanWidth, loadedCount);
  const soundOnlyFirst = groups.direct_syn.length === 0
    && groups.semantic_related.length === 0
    && groups.sound_only.length > 0;
  const [expandedEmptyGroups, setExpandedEmptyGroups] = useState<Set<CandidateGroup>>(() => new Set());

  return (
    <section className={`candidate-area${relaxed ? ' is-relaxed' : ''}`} aria-labelledby="candidateHeading">
      <p className="eyebrow">{relaxed ? '已確認放寬，非完全符合' : '由你揀，不代你寫'}</p>
      <h2 id="candidateHeading">{relaxed ? '放寬後結果' : '替換候選'}</h2>
      <p className="candidate-count" role="status">{status}</p>
      {poolTip ? (
        <p className="candidate-empty-tip" role="status">{poolTip}</p>
      ) : null}
      {semanticGap ? (
        <p className="semantic-gap" role="status">
          未有足夠近義資料；以下只按聲韻與詞頻排列，不是「沒有近義詞」的意思。
        </p>
      ) : null}
      <div>
        <div className={`candidate-groups${soundOnlyFirst ? ' candidate-groups--sound-first' : ''}`}>
          {GROUPS.map(([key, label]) => {
            const collapsible = COLLAPSIBLE_EMPTY_GROUPS.has(key) && groups[key].length === 0;
            const expanded = !collapsible || expandedEmptyGroups.has(key);
            return (
          <section className={`candidate-group${collapsible && !expanded ? ' is-collapsed' : ''}`} key={key} aria-labelledby={`candidate-${key}`}>
            <h3 id={`candidate-${key}`} tabIndex={-1}>
              {collapsible ? (
                <button
                  type="button"
                  className="candidate-group__toggle"
                  aria-expanded={expanded}
                  aria-controls={`candidate-${key}-content`}
                  onClick={() => setExpandedEmptyGroups((current) => {
                    const next = new Set(current);
                    if (next.has(key)) next.delete(key);
                    else next.add(key);
                    return next;
                  })}
                >
                  <span className="candidate-group__label">{label}</span>
                  <span className="candidate-group__count">{groups[key].length}</span>
                  <span className="candidate-group__toggle-icon" aria-hidden="true">{expanded ? '−' : '+'}</span>
                </button>
              ) : <><span className="candidate-group__label">{label}</span><span className="candidate-group__count">{groups[key].length}</span></>}
            </h3>
            <div id={`candidate-${key}-content`} className="candidate-group__content" hidden={collapsible && !expanded}>
            {groups[key].length ? (
              <div className="candidate-grid">
                {groups[key].map((candidate) => {
                  return (
                    <button
                      type="button"
                      className="candidate-card"
                      data-literal-length={compactEntryLength(candidate.literal)}
                      key={`${candidate.literal}-${candidate.jyutping}`}
                      onClick={(event) => onPreview(candidate, event.currentTarget)}
                    >
                      <span className="candidate-card__literal">{candidate.literal}</span>
                      <span className="candidate-card__code">{candidate.code}</span>
                    </button>
                  );
                })}
              </div>
            ) : <p className="empty-group">這一組暫時沒有候選。</p>}
            </div>
          </section>
            );
          })}
        </div>
        {hasMore && onLoadMore ? (
          <div className="candidate-load-more">
            <button type="button" onClick={onLoadMore} disabled={loadingMore}>
              {loadingMore ? '載入中…' : '載入更多'}
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
});
