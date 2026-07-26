import type { MouseEventHandler, Ref } from 'react';
import type { GuideMode } from '../guide-examples';
import type { QueryResult } from '../db/query.ts';
import type { EntryPickPayload } from '../result-list-logic.ts';
import { ResultList } from '../result-list';
import { SynResultList } from '../syn-result-list';
import { AnchorResultList } from '../anchor-result-list';
import { GuideQuick } from '../guide-quick';
import { countResultsRender } from '../search-perf.ts';

export interface QueryWorkspaceResultsBoundaryProps {
  detailOpen: boolean;
  showGuideQuick: boolean;
  filteredResults: QueryResult[];
  displayHint: string | null;
  loadingVisible: boolean;
  searchingLabel: string;
  error: Error | null;
  resultsLabel: string;
  synLayout: boolean;
  anchorLayout: boolean;
  visibleCount: number;
  activeLiteral: string | null;
  lang: 'zh' | 'zh-Hans' | 'en';
  inputQuery: string;
  emptyMessage: { primary: string; secondary?: string } | null;
  filterEmpty: boolean;
  hasMore: boolean;
  noLoadedResults: string;
  loadingMoreLabel: string;
  resetFilterLabel: string;
  guideQuickDisabled: boolean;
  showSentinel: boolean;
  scrollRootRef: Ref<HTMLDivElement>;
  sentinelRef: Ref<HTMLDivElement>;
  onMainClick: MouseEventHandler<HTMLDivElement>;
  onSynPick: (word: string) => void;
  onEntryPick: (payload: EntryPickPayload) => void;
  onRunExample: (query: string, mode: GuideMode) => void;
  onOpenFullGuide: () => void;
}

export function QueryWorkspaceResultsBoundary({
  detailOpen,
  showGuideQuick,
  filteredResults,
  displayHint,
  loadingVisible,
  searchingLabel,
  error,
  resultsLabel,
  synLayout,
  anchorLayout,
  visibleCount,
  activeLiteral,
  lang,
  inputQuery,
  emptyMessage,
  filterEmpty,
  hasMore,
  noLoadedResults,
  loadingMoreLabel,
  resetFilterLabel,
  guideQuickDisabled,
  showSentinel,
  scrollRootRef,
  sentinelRef,
  onMainClick,
  onSynPick,
  onEntryPick,
  onRunExample,
  onOpenFullGuide,
}: QueryWorkspaceResultsBoundaryProps) {
  countResultsRender();
  return (
    <section
      className={`search-view${detailOpen ? ' has-entry-detail' : ''}${showGuideQuick ? ' is-empty-landing' : ''}`}
      aria-labelledby="searchTitle"
    >
      <div className="search-view__main" onClick={onMainClick}>
        <div className="search-results">
          <div className="search-results-scroll" ref={scrollRootRef}>
            {displayHint && filteredResults.length > 0 ? <p className="search-hint">{displayHint}</p> : null}
            {loadingVisible ? (
              <p className="loading" role="status" aria-live="polite" aria-atomic="true">
                {searchingLabel}
              </p>
            ) : null}
            {error ? (
              <p className="error" role="alert" aria-live="assertive">
                錯誤: {error.message}
              </p>
            ) : null}

            {filteredResults.length > 0 ? (
              <div className="results-list">
                {resultsLabel ? (
                  <p className="results-count" aria-live="polite" aria-atomic="true">
                    {resultsLabel}
                  </p>
                ) : null}
                {synLayout ? (
                  <SynResultList
                    results={filteredResults}
                    visibleLimit={visibleCount}
                    onPick={onSynPick}
                  />
                ) : anchorLayout ? (
                  <AnchorResultList
                    results={filteredResults}
                    visibleLimit={visibleCount}
                    activeLiteral={activeLiteral}
                    lang={lang}
                    onPick={onEntryPick}
                  />
                ) : (
                  <ResultList
                    results={filteredResults}
                    showReadingBadge={inputQuery.includes('/')}
                    visibleLimit={visibleCount}
                    activeLiteral={activeLiteral}
                    lang={lang}
                    onPick={onEntryPick}
                  />
                )}
              </div>
            ) : null}

            {emptyMessage ? (
              <div className="no-results info">
                <p><strong>{emptyMessage.primary}</strong></p>
                {emptyMessage.secondary ? <p>{emptyMessage.secondary}</p> : null}
              </div>
            ) : null}

            {filterEmpty ? (
              <div className="no-results info">
                <p><strong>{noLoadedResults}</strong></p>
                <p>{hasMore ? loadingMoreLabel : resetFilterLabel}</p>
              </div>
            ) : null}

            {showGuideQuick ? (
              <GuideQuick
                lang={lang}
                disabled={guideQuickDisabled}
                onPick={onRunExample}
                onOpenFullGuide={onOpenFullGuide}
              />
            ) : null}

            {showSentinel ? <div ref={sentinelRef} className="results-scroll-sentinel" aria-hidden /> : null}
          </div>
        </div>
      </div>
    </section>
  );
}
