import type { QueryResult } from './db/query';
import { mergeResultsByLiteral } from '../../frontend/entry-detail-core.mjs';
import { tDetail } from '../../frontend/entry-detail-i18n.mjs';
import {
  displayResults,
  resultsShowReadingBadge,
  type EntryPickPayload,
} from './result-list-logic.ts';

export { resultsShowReadingBadge } from './result-list-logic.ts';

export function ResultList({
  results,
  committedQuery,
  visibleLimit,
  activeLiteral,
  lang = 'zh',
  onPick,
}: {
  results: QueryResult[];
  /** 輸入框／查詢字串；含 `/` 先顯示多讀音徽章（PWA 跟即時輸入） */
  committedQuery?: string | null;
  visibleLimit?: number;
  activeLiteral?: string | null;
  lang?: 'zh' | 'en';
  onPick: (payload: EntryPickPayload) => void;
}) {
  const rows = displayResults(results);
  const merged = mergeResultsByLiteral(rows);
  if (!merged.length) return null;
  const shown = visibleLimit != null ? merged.slice(0, visibleLimit) : merged;
  const showReadingBadge = resultsShowReadingBadge(committedQuery);

  return (
    <ul className="results-list-items">
      {shown.map((group) => {
        const primary = group.readings[0];
        const pickJyutping = primary?.jyutping;
        const isActive = activeLiteral === group.literal;
        const badgeN = showReadingBadge && group.readingCount > 1 ? group.readingCount : 0;
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
              aria-label={`${group.literal}${badgeN ? ` ${tDetail('detail.readings.n', lang, { n: badgeN })}` : ''}`}
            >
              <span className="word result-literal-only">{group.literal}</span>
              {badgeN ? (
                <span className="result-reading-badge">
                  {tDetail('detail.readings.n', lang, { n: badgeN })}
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
