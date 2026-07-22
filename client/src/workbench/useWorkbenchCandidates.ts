import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { PosFilterState } from '../pos/filter.ts';
import { resetPosFilter } from '../pos/filter.ts';
import type { ReplacementPlanV1 } from './contracts.ts';
import {
  candidateSessionView,
  emptyCandidateSession,
  requestLoadMore,
  rebindSelectionVersion,
  resetWithPlan,
  runCandidateFetch,
  samePlanIdentity,
  setPosFilter,
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
  enabled = true,
) {
  const defaultAdapter = useMemo(() => selectWorkbenchAdapter(), []);
  const activeAdapter = adapter ?? defaultAdapter;
  const findCandidates = useCallback(
    (req: ReplacementPlanV1, signal?: AbortSignal) => activeAdapter.findCandidates(req, signal),
    [activeAdapter],
  );

  const [state, setState] = useState<CandidateSessionState>(() => emptyCandidateSession());
  const stateRef = useRef(state);
  const activeFetchRef = useRef<AbortController | null>(null);
  stateRef.current = state;

  useEffect(() => () => activeFetchRef.current?.abort(), []);

  useEffect(() => {
    if (enabled) return;
    activeFetchRef.current?.abort();
    activeFetchRef.current = null;
  }, [enabled]);

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
  }, [plan]);

  useEffect(() => {
    if (!enabled) return;
    const current = stateRef.current;
    const planChanged = !samePlanIdentity(current.planBase, base);
    const posChanged = JSON.stringify(current.posFilter) !== JSON.stringify(posFilter);
    const versionChanged = current.planBase?.selectionVersion !== base?.selectionVersion;
    if (!planChanged && !posChanged && !versionChanged) return;

    activeFetchRef.current?.abort();
    activeFetchRef.current = null;

    let next = planChanged
      ? resetWithPlan(current, base, posFilter)
      : setPosFilter(current, posFilter);
    if (!planChanged && base && versionChanged) {
      next = rebindSelectionVersion(next, base);
    }
    setState(next);
    if (!base || !next.loading) return;

    const controller = new AbortController();
    activeFetchRef.current = controller;
    const startedGen = next.generation;
    void (async () => {
      const result = await runCandidateFetch(next, findCandidates, controller.signal);
      if (controller.signal.aborted) return;
      if (activeFetchRef.current === controller) activeFetchRef.current = null;
      setState((s) => (s.generation === startedGen ? result : s));
    })();
    return () => {
      controller.abort();
      if (activeFetchRef.current === controller) activeFetchRef.current = null;
    };
  }, [base, posFilter, findCandidates, enabled]);

  const loadMore = useCallback(() => {
    if (!enabled) return;
    setState((current) => {
      const view = candidateSessionView(current);
      if (!view.hasMore || current.loading) return current;
      const next = requestLoadMore(current);
      if (next.generation === current.generation) return current;
      const startedGen = next.generation;
      activeFetchRef.current?.abort();
      const controller = new AbortController();
      activeFetchRef.current = controller;
      void (async () => {
        const result = await runCandidateFetch(next, findCandidates, controller.signal);
        if (controller.signal.aborted) return;
        if (activeFetchRef.current === controller) activeFetchRef.current = null;
        setState((s) => (s.generation === startedGen ? result : s));
      })();
      return next;
    });
  }, [findCandidates, enabled]);

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
