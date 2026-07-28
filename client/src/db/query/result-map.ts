/** Result mapping / mask-family sort helpers (not parse classification). */
import type { Database } from '../sqljs.ts';
import { searchCompoundTiers } from '../compound.ts';
import {
  compareSearchResults,
  literalPriorityCompare,
  sortWordRows,
} from '../ranking.ts';
import { compoundSearchSpecFromMatchSpec } from '../position-match/sources.ts';
import type { CanonicalMatchSpec } from '../position-match/canonical.ts';
import { getWordText } from '../position-match/word-row.ts';
import type { WordRow } from '../position-match/word-row.ts';
import type { QueryMode, QueryResult } from '../query-types.ts';

/** Map lyrics.db row (`char`) to UI-facing QueryResult (`word`). */
export function rowToResult(row: Record<string, unknown>): QueryResult {
  const item: QueryResult = {
    word: String(row.char ?? ''),
    jyutping: String(row.jyutping ?? ''),
    code: String(row.code ?? ''),
    score: 0,
  };
  const dim = row.anchor_dimension;
  if (dim === 'initial' || dim === 'final') {
    item.anchor_dimension = dim;
  }
  return item;
}

export async function sortMaskFamilyRows(
  spec: CanonicalMatchSpec,
  rows: WordRow[],
  db: Database,
  _mode: QueryMode,
): Promise<WordRow[]> {
  if (spec.phoneme_alternatives) {
    return rows;
  }
  const literalPositions = [...spec.mask]
    .map((char, pos) => (/[\p{Script=Han}]/u.test(char) ? [pos, char] as [number, string] : null))
    .filter((item): item is [number, string] => item != null);
  if (spec.ranking === 'literal_priority' && literalPositions.length) {
    return [...rows].sort((a, b) => literalPriorityCompare(a, b, literalPositions));
  }
  if (spec.compound) {
    const compoundSpec = compoundSearchSpecFromMatchSpec(spec);
    if (!compoundSpec) {
      return sortWordRows(rows);
    }
    const tiers = await searchCompoundTiers(db, compoundSpec);
    return [...rows].sort((a, b) => {
      const ta = tiers.get(getWordText(a)) ?? 99;
      const tb = tiers.get(getWordText(b)) ?? 99;
      if (ta !== tb) {
        return ta - tb;
      }
      return compareSearchResults(a, b);
    });
  }
  return sortWordRows(rows);
}
