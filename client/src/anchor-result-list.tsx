import type { QueryResult } from './db/query';
import { ResultList } from './result-list';

function sectionTitle(title: string, count: number): string {
  return count > 0 ? `${title} (${count})` : title;
}

function AnchorSection({
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
      {items.length > 0 ? (
        <ResultList results={items} onPick={onPick} />
      ) : (
        <p className="syn-empty">無可用結果</p>
      )}
    </section>
  );
}

export function anchorResultsStats(results: QueryResult[], total?: number | null): string {
  const initial = results.filter((r) => r.anchor_dimension === 'initial').length;
  const final = results.filter((r) => r.anchor_dimension === 'final').length;
  const loaded = results.length;
  if (total != null && total > loaded) {
    return `聲母 ${initial}　韻母 ${final}（已載入 ${loaded} / ${total}）`;
  }
  return `聲母 ${initial}　韻母 ${final}（已載入 ${loaded}）`;
}

export function hasAnchorResultLayout(results: QueryResult[]): boolean {
  return results.some((r) => r.anchor_dimension === 'initial' || r.anchor_dimension === 'final');
}

export function AnchorResultList({
  results,
  onPick,
}: {
  results: QueryResult[];
  onPick: (query: string) => void;
}) {
  const initial = results.filter((r) => r.anchor_dimension === 'initial');
  const final = results.filter((r) => r.anchor_dimension === 'final');

  return (
    <div className="syn-container">
      <AnchorSection title="聲母" items={initial} onPick={onPick} />
      <AnchorSection title="韻母" items={final} onPick={onPick} />
    </div>
  );
}

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p5-anchor-self-check.ts` */
export function anchorResultListSelfCheck(): void {
  const rows: QueryResult[] = [
    { word: '唔', jyutping: 'm4', code: '44', anchor_dimension: 'initial' },
    { word: '五', jyutping: 'ng5', code: '45', anchor_dimension: 'final' },
  ];
  if (!hasAnchorResultLayout(rows)) {
    throw new Error('anchorResultListSelfCheck: layout detection');
  }
  const stats = anchorResultsStats(rows);
  if (!stats.includes('聲母 1') || !stats.includes('韻母 1')) {
    throw new Error(`anchorResultListSelfCheck: stats ${stats}`);
  }
}
