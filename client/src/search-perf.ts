/**
 * Dev-only search UI timing (?perf=1). No production console spam.
 * Read marks via performance.getEntriesByType('measure') / window.__searchPerf.
 */

export type SearchPerfState = {
  listRenders: number;
};

declare global {
  interface Window {
    __searchPerf?: SearchPerfState;
  }
}

let cached: boolean | null = null;

export function isSearchPerfEnabled(): boolean {
  if (cached != null) return cached;
  if (typeof location === 'undefined') {
    cached = false;
    return false;
  }
  cached = new URLSearchParams(location.search).has('perf');
  return cached;
}

function ensureState(): SearchPerfState {
  if (!window.__searchPerf) {
    window.__searchPerf = { listRenders: 0 };
  }
  return window.__searchPerf;
}

/** keydown/input → next animation frame (paint approximation). */
export function markInputChange(): void {
  if (!isSearchPerfEnabled()) return;
  performance.mark('search-perf:input-change');
  requestAnimationFrame(() => {
    try {
      performance.measure(
        'search-perf:input-to-frame',
        'search-perf:input-change',
      );
    } catch {
      /* mark cleared or missing */
    }
  });
}

export function markSearchDispatch(): void {
  if (!isSearchPerfEnabled()) return;
  performance.mark('search-perf:search-dispatch');
}

export function markSearchResolve(): void {
  if (!isSearchPerfEnabled()) return;
  performance.mark('search-perf:search-resolve');
  try {
    performance.measure(
      'search-perf:engine',
      'search-perf:search-dispatch',
      'search-perf:search-resolve',
    );
  } catch {
    /* dispatch mark missing (cancelled / first paint) */
  }
}

export function countListRender(): void {
  if (!isSearchPerfEnabled()) return;
  ensureState().listRenders += 1;
}

/** ponytail: `npx tsx client/scripts/search-perf-self-check.ts` */
export function searchPerfSelfCheck(): void {
  // Default (Node / no ?perf): helpers must no-op without touching window state
  markInputChange();
  markSearchDispatch();
  markSearchResolve();
  countListRender();
  if (typeof window !== 'undefined' && !isSearchPerfEnabled() && window.__searchPerf) {
    throw new Error('searchPerfSelfCheck: counted while disabled');
  }
}
