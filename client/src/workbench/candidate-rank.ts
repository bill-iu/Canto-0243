import { compareSearchResults } from '../db/ranking.ts';
import type { WorkbenchCandidate } from './contracts.ts';

export interface RelationRank {
  rank: number;
  source?: string;
}

export function relationIndex(rows: Array<{ char: string; source?: string }>): Map<string, RelationRank> {
  return new Map(rows.filter((row) => row.char).map((row, rank) => [row.char, { rank, source: row.source }]));
}

/** sound_only follows the canonical frequency ranking, not the source page offset. */
export function compareSoundOnlyCandidates(a: WorkbenchCandidate, b: WorkbenchCandidate): number {
  const ranked = compareSearchResults(
    { char: a.literal, jyutping: a.jyutping },
    { char: b.literal, jyutping: b.jyutping },
  );
  return ranked
    || a.sourceRank - b.sourceRank
    || a.code.localeCompare(b.code);
}
