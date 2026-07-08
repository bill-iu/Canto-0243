import type { QueryResult } from './db/query';
import { mergeResultsByLiteral, isListableWordRow } from '../../frontend/entry-detail-core.mjs';
import { tDetail } from '../../frontend/entry-detail-i18n.mjs';

export function displayResults(results: QueryResult[]): QueryResult[] {
  const seen = new Set<string>();
  return results.filter((row) => {
    if (!isListableWordRow(row)) return false;
    const key = `${row.word}\0${row.jyutping ?? ''}\0${row.code ?? ''}`;
    if (!row.word || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export type EntryPickPayload = {
  literal: string;
  jyutping?: string;
};

function resultKey(row: QueryResult, index: number): string {
  return `word-${row.word}-${row.code}-${row.jyutping}-${index}`;
}

export function ResultList({
  results,
  activeLiteral,
  lang = 'zh',
  onPick,
}: {
  results: QueryResult[];
  activeLiteral?: string | null;
  lang?: 'zh' | 'en';
  onPick: (payload: EntryPickPayload) => void;
}) {
  const rows = displayResults(results);
  const merged = mergeResultsByLiteral(rows);
  if (!merged.length) return null;

  return (
    <ul className="results-list-items">
      {merged.map((group) => {
        const primary = group.readings[0];
        const pickJyutping = primary?.jyutping;
        const isActive = activeLiteral === group.literal;
        return (
          <li key={group.literal} className={`result-item${isActive ? ' is-detail-active' : ''}`}>
            <button
              type="button"
              className="result-link"
              onClick={() => onPick({ literal: group.literal, jyutping: pickJyutping })}
              aria-label={`${group.literal}${group.readingCount > 1 ? ` ${tDetail('detail.readings.n', lang, { n: group.readingCount })}` : ''}`}
            >
              <span className="word result-literal-only">{group.literal}</span>
              {group.readingCount > 1 ? (
                <span className="result-reading-badge">
                  {tDetail('detail.readings.n', lang, { n: group.readingCount })}
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export { resultKey };