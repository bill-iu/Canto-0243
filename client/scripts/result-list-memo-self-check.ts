/**
 * Memo prop contract for ResultList H1 gate.
 * Typing without `/` must keep showReadingBadge false so React.memo skips.
 * `npx tsx client/scripts/result-list-memo-self-check.ts`
 */
import { resultsShowReadingBadge } from '../src/result-list-logic.ts';

type ListProps = {
  results: unknown;
  showReadingBadge: boolean;
  visibleLimit: number;
  activeLiteral: string | null;
  lang: 'zh' | 'en';
};

function listPropsStable(a: ListProps, b: ListProps): boolean {
  return (
    Object.is(a.results, b.results) &&
    a.showReadingBadge === b.showReadingBadge &&
    a.visibleLimit === b.visibleLimit &&
    a.activeLiteral === b.activeLiteral &&
    a.lang === b.lang
  );
}

const results: unknown[] = [];
const base = {
  results,
  visibleLimit: 400,
  activeLiteral: null as string | null,
  lang: 'zh' as const,
};

const before = { ...base, showReadingBadge: resultsShowReadingBadge('23') };
const afterDigit = { ...base, showReadingBadge: resultsShowReadingBadge('232') };
const afterSlash = { ...base, showReadingBadge: resultsShowReadingBadge('23/') };

if (!listPropsStable(before, afterDigit)) {
  throw new Error('result-list-memo-self-check: digit typing should keep memo props equal');
}
if (listPropsStable(before, afterSlash)) {
  throw new Error('result-list-memo-self-check: slash flip must change showReadingBadge');
}

console.log('result-list-memo-self-check ok');
