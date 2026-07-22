import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { PosFilterState } from '../pos/filter.ts';
import { resetPosFilter } from '../pos/filter.ts';
import type { ReplacementPlanV1 } from './contracts.ts';
import {
  candidateSessionView,
  emptyCandidateSession,
  requestLoadMore,
  resetWithPlan,
  runCandidateFetch,
  samePlanIdentity,
  type CandidatePlanBase,
  type CandidateSessionState,
} from './candidate-session/index.ts';
import { selectWorkbenchAdapter, type WorkbenchAdapter } from './workbench-adapter.ts';

/**
 * Thin React shell over candidate-session (P2#4).
 * Pass plan **without** relying on page-owned offset — session owns engine cursor.
 * `plan` may still include offset/limit; they are ignored for identity (stripped).
 */
export function useWorkbenchCandidates(
  plan: ReplacementPlanV1 | CandidatePlanBase | null,
  adapter?: WorkbenchAdapter,
  posFilter: PosFilterState = resetPosFilter(),
) {
  const defaultAdapter = useMemo(() => selectWorkbenchAdapter(), []);
  const activeAdapter = adapter ?? defaultAdapter;
  const findCandidates = useCallback(
    (req: ReplacementPlanV1, signal?: AbortSignal) => activeAdapter.findCandidates(req, signal),
    [activeAdapter],
  );

  const [state, setState] = useState<CandidateSessionState>(() => emptyCandidateSession());
  const stateRef = useRef(state);
  stateRef.current = state;

  const base: CandidatePlanBase | null = useMemo(() => {
    if (!plan) return null;
    return {
      version: plan.version,
      selectionVersion: plan.selectionVersion,
      width: plan.width,
      mode: plan.mode,
      slots: plan.slots,
      semanticIntent: plan.semanticIntent,
      semanticSeed: plan.semanticSeed,
    };
  }, [
    plan?.version,
    plan?.selectionVersion,
    plan?.width,
    plan?.mode,
    plan?.semanticIntent,
    plan?.semanticSeed,
    // slots identity
    plan ? JSON.stringify(plan.slots) : '',
  ]);

  useEffect(() => {
    const current = stateRef.current;
    const planChanged = !samePlanIdentity(current.planBase, base);
    const posChanged = JSON.stringify(current.posFilter) !== JSON.stringify(posFilter);
    if (!planChanged && !posChanged) return;

    const next = resetWithPlan(current, base, posFilter);
    setState(next);
    if (!base) return;

    const controller = new AbortController();
    const startedGen = next.generation;
    void (async () => {
      const result = await runCandidateFetch(next, findCandidates, controller.signal);
      if (controller.signal.aborted) return;
      setState((s) => (s.generation === startedGen ? result : s));
    })();
    return () => controller.abort();
  }, [base, posFilter, findCandidates]);

  const loadMore = useCallback(() => {
    setState((current) => {
      const view = candidateSessionView(current);
      if (!view.hasMore || current.loading) return current;
      const next = requestLoadMore(current);
      if (next.generation === current.generation) return current;
      const startedGen = next.generation;
      void (async () => {
        const result = await runCandidateFetch(next, findCandidates);
        setState((s) => (s.generation === startedGen ? result : s));
      })();
      return next;
    });
  }, [findCandidates]);

  const view = useMemo(() => candidateSessionView(state), [state]);

  return {
    response: view.response,
    error: view.error,
    loading: view.loading,
    loadedCount: view.filteredCount,
    fetchedCount: view.engineFetched,
    engineTotal: view.engineTotal,
    hasMore: view.hasMore,
    loadMore,
  };
}

export { applyCreatorPosFilter } from './candidate-session/index.ts';
