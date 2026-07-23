import { memo } from 'react';
import type { QueryResult } from './db/query';
import { synResultItemCount } from './syn-result-logic.ts';
import { countListRender } from './search-perf.ts';

function sectionTitle(title: string, count: number): string {
  return count > 0 ? `${title} (${count})` : title;
}

function itemTitle(row: QueryResult): string {
  const parts: string[] = [];
  if (row.source) {
    parts.push(`來源：${row.source}`);
  }
  return parts.join(' · ');
}

function SynSection({
  title,
  items,
  onPick,
}: {
  title: string;
  items: QueryResult[];
  onPick: (query: string) => void;
}) {
  return (
    <section className="syn-section">
      <h2 className="syn-section__title">{sectionTitle(title, items.length)}</h2>
      <div className="syn-section__grid">
        {items.length > 0 ? (
          items.map((row, index) => (
            <button
              key={`${row.word}-${index}`}
              type="button"
              className="syn-chip"
              title={itemTitle(row) || undefined}
              onClick={() => onPick(row.word)}
              aria-label={`搜尋 ${row.word}`}
            >
              {row.word}
            </button>
          ))
        ) : (
          <p className="syn-empty">無可用結果</p>
        )}
      </div>
    </section>
  );
}

function takeSynBudget(
  syns: QueryResult[],
  ants: QueryResult[],
  related: QueryResult[],
  budget: number,
) {
  const synsShown = syns.slice(0, budget);
  let left = budget - synsShown.length;
  const antsShown = ants.slice(0, Math.max(0, left));
  left -= antsShown.length;
  const relatedShown = related.slice(0, Math.max(0, left));
  return { synsShown, antsShown, relatedShown };
}

export const SynResultList = memo(function SynResultList({
  results,
  visibleLimit,
  onPick,
}: {
  results: QueryResult[];
  visibleLimit?: number;
  onPick: (query: string) => void;
}) {
  countListRender();
  const syns = results.filter((r) => r.relation === 'syn');
  const ants = results.filter((r) => r.relation === 'ant');
  const related = results.filter((r) => r.relation === 'semantic_related');
  const budget = visibleLimit ?? synResultItemCount(results);
  const { synsShown, antsShown, relatedShown } = takeSynBudget(syns, ants, related, budget);

  return (
    <div className="syn-container">
      <SynSection title="近義詞" items={synsShown} onPick={onPick} />
      <SynSection title="反義詞" items={antsShown} onPick={onPick} />
      {related.length > 0 ? <SynSection title="語意相關" items={relatedShown} onPick={onPick} /> : null}
    </div>
  );
});
