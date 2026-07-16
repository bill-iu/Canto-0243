import type { QueryResult } from './db/query';
import { mergeResultsByLiteral } from '../../shared/entry-detail-core.mjs';
import { ResultList } from './result-list';
import { type EntryPickPayload } from './result-list-logic.ts';
import { anchorResultItemCount } from './anchor-result-logic.ts';

function sectionTitle(title: string, count: number): string {
  return count > 0 ? `${title} (${count})` : title;
}

function AnchorSection({
  title,
  items,
  activeLiteral,
  lang,
  onPick,
}: {
  title: string;
  items: QueryResult[];
  activeLiteral?: string | null;
  lang?: 'zh' | 'en';
  onPick: (payload: EntryPickPayload) => void;
}) {
  return (
    <section className="syn-section">
      <h2 className="syn-section__title">{sectionTitle(title, items.length)}</h2>
      {items.length > 0 ? (
        <ResultList results={items} activeLiteral={activeLiteral} lang={lang} onPick={onPick} />
      ) : (
        <p className="syn-empty">無可用結果</p>
      )}
    </section>
  );
}

export function AnchorResultList({
  results,
  visibleLimit,
  activeLiteral,
  lang,
  onPick,
}: {
  results: QueryResult[];
  visibleLimit?: number;
  activeLiteral?: string | null;
  lang?: 'zh' | 'en';
  onPick: (payload: EntryPickPayload) => void;
}) {
  const initial = results.filter((r) => r.anchor_dimension === 'initial');
  const final = results.filter((r) => r.anchor_dimension === 'final');
  const budget = visibleLimit ?? anchorResultItemCount(results);
  const initialMerged = mergeResultsByLiteral(
    initial.map((row) => ({ ...row, word: row.char || row.display_text || row.word })),
  );
  const finalMerged = mergeResultsByLiteral(
    final.map((row) => ({ ...row, word: row.char || row.display_text || row.word })),
  );
  const initialShown = initialMerged.slice(0, budget);
  const finalShown = finalMerged.slice(0, Math.max(0, budget - initialShown.length));
  const initialRows = initialShown.map((group) => ({
    word: group.literal,
    char: group.literal,
    jyutping: group.readings[0]?.jyutping,
    code: group.readings[0]?.code,
    anchor_dimension: 'initial' as const,
  }));
  const finalRows = finalShown.map((group) => ({
    word: group.literal,
    char: group.literal,
    jyutping: group.readings[0]?.jyutping,
    code: group.readings[0]?.code,
    anchor_dimension: 'final' as const,
  }));

  return (
    <div className="syn-container">
      <AnchorSection title="聲母" items={initialRows} activeLiteral={activeLiteral} lang={lang} onPick={onPick} />
      <AnchorSection title="韻母" items={finalRows} activeLiteral={activeLiteral} lang={lang} onPick={onPick} />
    </div>
  );
}
