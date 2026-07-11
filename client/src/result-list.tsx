import type { QueryResult } from './db/query';
import { mergeResultsByLiteral } from '../../frontend/entry-detail-core.mjs';
import { tDetail } from '../../frontend/entry-detail-i18n.mjs';
import { displayResults, type EntryPickPayload } from './result-list-logic.ts';

export function ResultList({
  results,
  visibleLimit,
  activeLiteral,
  lang = 'zh',
  onPick,
}: {
  results: QueryResult[];
  visibleLimit?: number;
  activeLiteral?: string | null;
  lang?: 'zh' | 'en';
  onPick: (payload: EntryPickPayload) => void;
}) {
  const rows = displayResults(results);
  const merged = mergeResultsByLiteral(rows);
  if (!merged.length) return null;
  const shown = visibleLimit != null ? merged.slice(0, visibleLimit) : merged;

  return (
    <ul className="results-list-items">
      {shown.map((group) => {
        const primary = group.readings[0];
        const pickJyutping = primary?.jyutping;
        const isActive = activeLiteral === group.literal;
        return (
          <li key={group.literal} className={`result-item${isActive ? ' is-detail-active' : ''}`}>
            <button
              type="button"
              className="result-link result-link--inline"
              onClick={() =>
                onPick({
                  literal: group.literal,
                  jyutping: pickJyutping,
                  readings: group.readings.map((r) => ({
                    jyutping: r.jyutping,
                    code: r.code,
                  })),
                })
              }
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
