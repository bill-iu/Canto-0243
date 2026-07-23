import { memo } from 'react';
import type { QueryResult } from './db/query';
import { mergeResultsByLiteral } from '../../shared/entry-detail-core.mjs';
import { tDetail } from '../../shared/entry-detail-i18n.mjs';
import {
  displayResults,
  resultItemGridSpan,
  type EntryPickPayload,
} from './result-list-logic.ts';
import { countListRender } from './search-perf.ts';

export const ResultList = memo(function ResultList({
  results,
  showReadingBadge = false,
  visibleLimit,
  activeLiteral,
  lang = 'zh',
  onPick,
}: {
  results: QueryResult[];
  /** 「N個讀音」徽章；由呼叫端自 inputQuery 衍生，避免整段字串破 memo */
  showReadingBadge?: boolean;
  visibleLimit?: number;
  activeLiteral?: string | null;
  lang?: 'zh' | 'en';
  onPick: (payload: EntryPickPayload) => void;
}) {
  countListRender();
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
        const badgeN = showReadingBadge && group.readingCount > 1 ? group.readingCount : 0;
        const span = resultItemGridSpan(group.literal);
        return (
          <li
            key={group.literal}
            className={`result-item${isActive ? ' is-detail-active' : ''}`}
            data-literal-span={span}
          >
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
});
