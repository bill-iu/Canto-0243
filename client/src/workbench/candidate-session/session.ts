import { isPosFilterActive, resetPosFilter, type PosFilterState } from '../../pos/filter.ts';
import {
  WORKBENCH_CANDIDATE_PAGE_SIZE,
  WORKBENCH_POS_AUTO_SCAN_PAGES,
  type ReplacementPlanV1,
  type WorkbenchCandidateResponse,
} from '../contracts.ts';
import { shouldSkipCandidateQuery } from '../limits.ts';
import {
  applyCreatorPosFilter,
  engineTotalOf,
  groupCount,
  mergeGroups,
} from './groups.ts';
import type {
  CandidatePlanBase,
  CandidateSessionState,
  CandidateSessionView,
  FindCandidates,
} from './types.ts';

function emptyExactResponse(selectionVersion: number): WorkbenchCandidateResponse {
  return {
    version: 1,
    selectionVersion,
    exact: { direct_syn: [], semantic_related: [], sound_only: [] },
    total: 0,
    engineTotal: 0,
    relaxation: null,
  };
}

export function emptyCandidateSession(
  pageSize = WORKBENCH_CANDIDATE_PAGE_SIZE,
): CandidateSessionState {
  return {
    planBase: null,
    posFilter: resetPosFilter(),
    pageSize,
    engineCursor: 0,
    engineTotal: 0,
    filteredTarget: pageSize,
    raw: null,
    staleRaw: null,
    loading: false,
    error: null,
    generation: 0,
  };
}

export function resetWithPlan(
  state: CandidateSessionState,
  planBase: CandidatePlanBase | null,
  posFilter?: PosFilterState,
): CandidateSessionState {
  // 無 plan：清晒。有 plan：raw 清空給 fetch，staleRaw 留舊結果上屏。
  const keepStale = planBase ? (state.raw ?? state.staleRaw) : null;
  return {
    ...state,
    planBase,
    posFilter: posFilter ?? state.posFilter,
    engineCursor: 0,
    engineTotal: 0,
    filteredTarget: state.pageSize,
    raw: null,
    staleRaw: keepStale,
    loading: !!planBase,
    error: null,
    generation: state.generation + 1,
  };
}

export function setPosFilter(
  state: CandidateSessionState,
  posFilter: PosFilterState,
): CandidateSessionState {
  return resetWithPlan(state, state.planBase, posFilter);
}

export function requestLoadMore(state: CandidateSessionState): CandidateSessionState {
  if (!state.planBase) return state;
  if (state.raw != null && state.engineCursor >= state.engineTotal && state.engineTotal > 0) {
    return state;
  }
  return {
    ...state,
    filteredTarget: state.filteredTarget + state.pageSize,
    loading: true,
    error: null,
    generation: state.generation + 1,
  };
}

export function candidateSessionView(state: CandidateSessionState): CandidateSessionView {
  const fresh = state.raw != null;
  const raw = state.raw ?? state.staleRaw;
  if (!raw) {
    return {
      response: null,
      engineTotal: state.engineTotal,
      engineFetched: 0,
      filteredCount: 0,
      hasMore: false,
      loading: state.loading,
      error: state.error,
    };
  }
  const filtered = applyCreatorPosFilter(raw, state.posFilter);
  const engineFetched = groupCount(raw.exact);
  const filteredCount = groupCount(filtered.exact);
  const engineTotal = engineTotalOf(raw);
  // stale 期間唔報 hasMore／loadMore，避免用舊 cursor 加載
  const hasMore = fresh && state.engineCursor < engineTotal;
  return {
    response: filtered,
    engineTotal,
    engineFetched,
    filteredCount,
    hasMore,
    loading: state.loading,
    error: state.error,
  };
}

function mergePage(
  state: CandidateSessionState,
  page: WorkbenchCandidateResponse,
): CandidateSessionState {
  const total = engineTotalOf(page);
  const pageRows = groupCount(page.exact);
  const nextCursor = state.engineCursor + state.pageSize;
  let raw: WorkbenchCandidateResponse;
  if (!state.raw) {
    raw = {
      ...page,
      exact: {
        direct_syn: [...page.exact.direct_syn],
        semantic_related: [...page.exact.semantic_related],
        sound_only: [...page.exact.sound_only],
      },
      total,
      engineTotal: total,
    };
  } else {
    raw = {
      ...page,
      exact: mergeGroups(state.raw.exact, page.exact),
      relaxation: state.raw.relaxation ?? page.relaxation,
      total,
      engineTotal: total,
    };
  }
  return {
    ...state,
    raw,
    engineTotal: total,
    // 空頁或已盡：cursor 推到 total；否則按 pageSize 前進
    engineCursor: pageRows === 0 ? total : Math.min(nextCursor, total > 0 ? total : nextCursor),
  };
}

function buildRequestPlan(state: CandidateSessionState, offset: number): ReplacementPlanV1 {
  if (!state.planBase) throw new Error('candidate session: no plan');
  return {
    ...state.planBase,
    limit: state.pageSize,
    offset,
  };
}

function filteredCountOf(state: CandidateSessionState): number {
  if (!state.raw) return 0;
  return groupCount(applyCreatorPosFilter(state.raw, state.posFilter).exact);
}

function poolExhausted(state: CandidateSessionState): boolean {
  if (state.raw == null) return false;
  if (state.engineTotal <= 0 && groupCount(state.raw.exact) === 0) return true;
  return state.engineCursor >= state.engineTotal && state.engineTotal > 0;
}

/**
 * 執行直至展示列數 >= filteredTarget 或引擎池盡。
 * 呼叫前 state 應已 reset／requestLoadMore（loading + generation）。
 */
export async function runCandidateFetch(
  state: CandidateSessionState,
  findCandidates: FindCandidates,
  signal?: AbortSignal,
): Promise<CandidateSessionState> {
  if (!state.planBase) {
    return { ...state, loading: false, raw: null, staleRaw: null };
  }
  const startedGen = state.generation;
  // ADR-0069: width > lexicon max word length → skip engine (structural empty).
  if (shouldSkipCandidateQuery(state.planBase.width)) {
    const raw = emptyExactResponse(state.planBase.selectionVersion);
    return {
      ...state,
      loading: false,
      raw,
      staleRaw: null,
      engineTotal: 0,
      engineCursor: 0,
      error: null,
      generation: startedGen,
    };
  }
  // resetWithPlan 已 raw=null；loadMore 保留 raw 以便 merge
  let current = state;
  let fetchedPages = 0;

  try {
    while (!signal?.aborted) {
      if (filteredCountOf(current) >= current.filteredTarget) break;
      if (poolExhausted(current)) break;
      if (isPosFilterActive(current.posFilter) && fetchedPages >= WORKBENCH_POS_AUTO_SCAN_PAGES) break;

      const offset = current.raw == null ? 0 : current.engineCursor;
      const page = await findCandidates(buildRequestPlan(current, offset), signal);
      if (signal?.aborted) return current;
      if (page.selectionVersion !== current.planBase!.selectionVersion) return current;

      fetchedPages += 1;
      const before = current.engineCursor;
      current = mergePage(current, page);
      // 無進展（空頁且 cursor 未變）→ 停
      if (groupCount(page.exact) === 0 && current.engineCursor === before) break;
      if (groupCount(page.exact) === 0) break;
    }

    if (signal?.aborted) return current;
    return {
      ...current,
      loading: false,
      staleRaw: null,
      error: null,
      generation: startedGen,
    };
  } catch (err) {
    if (signal?.aborted) return current;
    return {
      ...current,
      loading: false,
      error: err instanceof Error ? err : new Error('candidate request failed'),
      generation: startedGen,
    };
  }
}

/** planBase 是否同一查詢身份（忽略 paging）。 */
export function samePlanIdentity(
  a: CandidatePlanBase | null,
  b: CandidatePlanBase | null,
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.selectionVersion === b.selectionVersion
    && a.width === b.width
    && a.mode === b.mode
    && a.semanticIntent === b.semanticIntent
    && a.semanticSeed === b.semanticSeed
    && JSON.stringify(a.slots) === JSON.stringify(b.slots)
  );
}
