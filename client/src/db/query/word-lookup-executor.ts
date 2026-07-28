/** Word / digit / jyutping fragment execution — mirror of WordLookupExecutor. */
import type { Database } from '../sqljs.ts';
import { queryRows } from '../database-backend.ts';
import { getCodeVariants } from '../code-variants.ts';
import { sortQueryResults } from '../ranking.ts';
import {
  expectedWordLength,
  matchesJyutpingQuery,
} from '../jyutping-match.ts';
import type {
  DigitCodeQuery,
  JyutpingFragmentQuery,
  QueryMode,
  SearchResult,
  WordLookupQuery,
} from '../query-types.ts';
import type { WordRow } from '../position-match/word-row.ts';
import { filterSingleDigitToPreferredReadings } from '../position-match/filters/f1-slot-code.ts';
import { rowToResult } from './result-map.ts';
import { buildLookupLayout, deduplicateWordRows } from './lookup-layout.ts';
import { composeTransientWordRows } from '../db-patch.ts';

/** m1 full loose / m2 4↔5 / m3 strict — must pass through to getCodeVariants. */
function searchModeForCode(mode: QueryMode): 'm1' | 'm2' | 'm3' {
  if (mode === 'm2' || mode === '02493') return 'm2';
  if (mode === 'm3' || mode === '394052') return 'm3';
  return 'm1';
}

export async function executeDigitCodeQuery(
  parsed: DigitCodeQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  const q = parsed.raw_q;
  const searchMode = searchModeForCode(mode);
  const variants = getCodeVariants(q, searchMode);
  const placeholders = variants.map(() => '?').join(', ');
  const len = q.length;

  const sql = `
    SELECT char, jyutping, code
    FROM words
    WHERE code IN (${placeholders})
      AND length = ?
  `;

  const rows = await queryRows(db, sql, [...variants, len]) as WordRow[];

  let narrowed: WordRow[] = rows;
  if (len === 1) {
    const chars = [...new Set(rows.map((r) => String(r.char ?? '')).filter(Boolean))];
    if (!chars.length) {
      return { items: [], total: 0 };
    }
    const charPlaceholders = chars.map(() => '?').join(', ');
    const allRows = (await queryRows(
      db,
      `SELECT char, jyutping, code FROM words WHERE length = 1 AND char IN (${charPlaceholders})`,
      chars,
    )) as WordRow[];
    narrowed = filterSingleDigitToPreferredReadings(allRows, new Set(variants));
  } else {
    narrowed = deduplicateWordRows(rows);
  }

  const sorted = sortQueryResults(narrowed.map((row) => rowToResult(row)));
  return { items: sorted.slice(offset, offset + limit), total: sorted.length };
}

export async function executeWordLookup(
  parsed: WordLookupQuery,
  db: Database,
  _mode: QueryMode,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  let matches = (await queryRows(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
    [parsed.raw_q],
  )) as WordRow[];

  // 缺庫：記憶體音節拼接（唔寫庫）— 對齊 Portable compose_transient_words
  if (!matches.length && /\p{Script=Han}/u.test(parsed.raw_q)) {
    matches = (await composeTransientWordRows(db, parsed.raw_q)) as WordRow[];
  }

  const built = await buildLookupLayout(parsed.raw_q, deduplicateWordRows(matches), db);
  return {
    items: built.slice(offset, offset + limit),
    total: built.length,
    lookup_layout: true,
  };
}

export async function executeJyutpingFragment(
  parsed: JyutpingFragmentQuery,
  db: Database,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  const wordLen = expectedWordLength(parsed.raw_q);
  if (wordLen == null) {
    return { items: [] };
  }

  const sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE length = ?
  `;
  const rows = (await queryRows(db, sql, [wordLen])) as WordRow[];
  const matched = deduplicateWordRows(rows).filter((row) =>
    matchesJyutpingQuery(String(row.jyutping ?? ''), parsed.raw_q),
  );
  const sorted = sortQueryResults(matched.map((row) => rowToResult(row)));
  return { items: sorted.slice(offset, offset + limit), total: sorted.length };
}
