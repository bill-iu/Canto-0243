import type { QueryResult } from './db/query';
import { mergeResultsByLiteral } from '../../shared/entry-detail-core.mjs';

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

export function anchorResultItemCount(results: QueryResult[]): number {
  const initial = results.filter((r) => r.anchor_dimension === 'initial');
  const final = results.filter((r) => r.anchor_dimension === 'final');
  const initialMerged = mergeResultsByLiteral(
    initial.map((row) => ({ ...row, word: row.char || row.display_text || row.word })),
  );
  const finalMerged = mergeResultsByLiteral(
    final.map((row) => ({ ...row, word: row.char || row.display_text || row.word })),
  );
  return initialMerged.length + finalMerged.length;
}

export function anchorResultListSelfCheck(): void {
  const rows: QueryResult[] = [
    { word: '唔', jyutping: 'm4', code: '44', score: 0, anchor_dimension: 'initial' },
    { word: '五', jyutping: 'ng5', code: '45', score: 0, anchor_dimension: 'final' },
  ];
  if (!hasAnchorResultLayout(rows)) {
    throw new Error('anchorResultListSelfCheck: layout detection');
  }
  const stats = anchorResultsStats(rows);
  if (!stats.includes('聲母 1') || !stats.includes('韻母 1')) {
    throw new Error(`anchorResultListSelfCheck: stats ${stats}`);
  }
}
