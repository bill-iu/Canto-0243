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
import { rowToResult } from './result-map.ts';
import { buildLookupLayout, deduplicateWordRows } from './lookup-layout.ts';
import { composeTransientWordRows } from '../db-patch.ts';

function normalizeSearchMode(mode: QueryMode): 'm1' | 'm2' {
  if (mode === 'm2' || mode === '02493') {
    return 'm2';
  }
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
  const searchMode = normalizeSearchMode(mode);
  const variants = getCodeVariants(q, searchMode);
  const placeholders = variants.map(() => '?').join(', ');
  const len = q.length;

  const sql = `
    SELECT char, jyutping, code
    FROM words
    WHERE code IN (${placeholders})
      AND (
        length = ?
        OR ((length IS NULL OR length = 0) AND length(char) = ?)
      )
  `;

  const rows = await queryRows(db, sql, [...variants, len, len]) as WordRow[];

  const sorted = sortQueryResults(deduplicateWordRows(rows).map((row) => rowToResult(row)));
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
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
  `;
  const rows = (await queryRows(db, sql, [wordLen, wordLen])) as WordRow[];
  const matched = deduplicateWordRows(rows).filter((row) =>
    matchesJyutpingQuery(String(row.jyutping ?? ''), parsed.raw_q),
  );
  const sorted = sortQueryResults(matched.map((row) => rowToResult(row)));
  return { items: sorted.slice(offset, offset + limit), total: sorted.length };
}
