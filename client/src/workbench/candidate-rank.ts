export interface RelationRank {
  rank: number;
  source?: string;
}

export function relationIndex(rows: Array<{ char: string; source?: string }>): Map<string, RelationRank> {
  return new Map(rows.filter((row) => row.char).map((row, rank) => [row.char, { rank, source: row.source }]));
}
