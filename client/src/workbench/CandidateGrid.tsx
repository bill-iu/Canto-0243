import type { CandidateGroups, WorkbenchCandidate } from './contracts.ts';
import { candidateReasonLabel } from './candidate-reason-i18n.ts';
import { emptyPoolTip } from './limits.ts';

const GROUPS: Array<[keyof CandidateGroups, string]> = [
  ['direct_syn', '直接近義'],
  ['semantic_related', '語意相關'],
  ['sound_only', '只合音格'],
];

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

export function CandidateGrid({
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
      {GROUPS.map(([key, label]) => (
        <section className="candidate-group" key={key} aria-labelledby={`candidate-${key}`}>
          <h3 id={`candidate-${key}`} tabIndex={-1}>{label}<span>{groups[key].length}</span></h3>
          {groups[key].length ? (
            <div className="candidate-grid">
              {groups[key].map((candidate) => {
                const wide = [...candidate.literal].length >= 7;
                return (
                  <button
                    type="button"
                    className={`candidate-card${wide ? ' candidate-card--wide' : ''}`}
                    key={`${candidate.literal}-${candidate.jyutping}`}
                    onClick={(event) => onPreview(candidate, event.currentTarget)}
                  >
                    <span className="candidate-card__literal">{candidate.literal}</span>
                    <span className="candidate-card__jyutping">{candidate.jyutping}</span>
                    <span className="candidate-card__code">{candidate.code}</span>
                    <span className="candidate-card__reason">
                      {relaxed
                        ? candidateReasonLabel('relaxed_constraint')
                        : candidateReasonLabel(candidate.reasons[0]!.kind)}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : <p className="empty-group">這一組暫時沒有候選。</p>}
        </section>
      ))}
      {hasMore && onLoadMore ? (
        <div className="candidate-load-more">
          <button type="button" onClick={onLoadMore} disabled={loadingMore}>
            {loadingMore ? '載入中…' : '載入更多'}
          </button>
        </div>
      ) : null}
    </section>
  );
}
