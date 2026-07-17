import type { CandidateGroups, WorkbenchCandidate } from './contracts.ts';
import { candidateReasonLabel } from './candidate-reason-i18n.ts';

const GROUPS: Array<[keyof CandidateGroups, string]> = [
  ['direct_syn', '直接近義'],
  ['semantic_related', '語意相關'],
  ['sound_only', '只合音格'],
];

interface Props {
  groups: CandidateGroups;
  relaxed?: { kind: string; from?: string; to?: string } | null;
  semanticGap?: boolean;
  onPreview: (candidate: WorkbenchCandidate, origin: HTMLButtonElement) => void;
}

export function CandidateGrid({ groups, relaxed, semanticGap, onPreview }: Props) {
  const sacrifice = relaxed
    ? [relaxed.kind, relaxed.from && relaxed.to ? `${relaxed.from} → ${relaxed.to}` : relaxed.from || relaxed.to]
      .filter(Boolean)
      .join(' · ')
    : '';
  return (
    <section className={`candidate-area${relaxed ? ' is-relaxed' : ''}`} aria-labelledby="candidateHeading">
      <p className="eyebrow">{relaxed ? '已確認放寬，非完全符合' : '由你揀，不代你寫'}</p>
      <h2 id="candidateHeading">{relaxed ? '放寬後結果' : '替換候選'}</h2>
      {relaxed ? <p className="relaxed-banner">實際犧牲：{sacrifice || relaxed.kind}</p> : null}
      {semanticGap ? (
        <p className="semantic-gap" role="status">
          未有足夠近義資料；以下只按聲韻與詞頻排列，不是「沒有近義詞」的意思。
        </p>
      ) : null}
      {GROUPS.map(([key, label]) => (
        <section className="candidate-group" key={key} aria-labelledby={`candidate-${key}`}>
          <h3 id={`candidate-${key}`}>{label}<span>{groups[key].length}</span></h3>
          {groups[key].length ? (
            <div className="candidate-grid">
              {groups[key].map((candidate) => (
                <button
                  type="button"
                  className="candidate-card"
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
              ))}
            </div>
          ) : <p className="empty-group">這一組暫時沒有候選。</p>}
        </section>
      ))}
    </section>
  );
}
